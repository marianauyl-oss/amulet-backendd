# -*- coding: utf-8 -*-
import os, json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from io import StringIO, BytesIO
from models import db, License, ApiKey, Voice, Config, ActivityLog

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

# Use DATABASE_URL from environment, fallback to SQLite in volume for Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:////app/storage/amulet.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ---------- DB init + seed ----------
with app.app_context():
    db.create_all()
    if Config.query.first() is None:
        cfg = Config(
            latest_version="1.0.0",
            force_update=False,
            maintenance=False,
            maintenance_message="",
            update_description="Initial config",
            update_links="https://example.com/download"
        )
        db.session.add(cfg)
        db.session.commit()

# ==================================================
# ================ PUBLIC API (/api) ===============
# ==================================================
@app.route("/api", methods=["POST"])
def public_api():
    data = request.get_json(force=True, silent=True) or {}
    action = (data.get("action") or "").strip()
    if action == "check":               return _api_check(data)
    if action == "debit":               return _api_debit(data)
    if action == "refund":              return _api_refund(data)
    if action == "next_api_key":        return _api_next_api_key()
    if action == "release_api_key":     return jsonify({"ok": True})
    if action == "deactivate_api_key":  return _api_deactivate_api_key(data)
    if action == "get_voices":          return _api_get_voices()
    if action == "get_config":          return _api_get_config()
    return jsonify({"ok": False, "msg": "Unknown action"})

def _api_check(req):
    key = (req.get("key") or "").strip()
    mac = (req.get("mac") or "").strip()
    if not key or not mac:
        return jsonify({"ok": False, "msg": "key/mac required"})
    lic = License.query.filter_by(key=key).first()
    if not lic: return jsonify({"ok": False, "msg": "License not found"})
    if not lic.active: return jsonify({"ok": False, "msg": "License inactive"})

    if not lic.mac_id:
        lic.mac_id = mac
        lic.updated_at = datetime.utcnow()
        db.session.commit()
    elif lic.mac_id != mac:
        return jsonify({"ok": False, "msg": "License activated on another device"})
    return jsonify({"ok": True, "credit": lic.credit})

def _api_debit(req):
    key = (req.get("key") or "").strip()
    mac = (req.get("mac") or "").strip()
    cnt = int(req.get("count") or 0)
    if not key or not mac: return jsonify({"ok": False, "msg": "key/mac required"})
    if cnt <= 0:           return jsonify({"ok": False, "msg": "count must be > 0"})

    lic = License.query.filter_by(key=key).first()
    if not lic: return jsonify({"ok": False, "msg": "License not found"})
    if not lic.active: return jsonify({"ok": False, "msg": "License inactive"})
    if lic.mac_id != mac: return jsonify({"ok": False, "msg": "MAC mismatch or not bound"})
    if lic.credit < cnt: return jsonify({"ok": False, "msg": "Insufficient credit", "credit": lic.credit})

    lic.credit -= cnt
    lic.updated_at = datetime.utcnow()
    # Log the debit action
    log = ActivityLog(
        license_id=lic.id,
        action="debit",
        char_count=cnt,
        details=f"Debited {cnt} credits for key {key}"
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True, "debited": cnt, "credit": lic.credit})

def _api_refund(req):
    key = (req.get("key") or "").strip()
    mac = (req.get("mac") or "").strip()
    cnt = int(req.get("count") or 0)
    if not key or not mac: return jsonify({"ok": False, "msg": "key/mac required"})
    if cnt <= 0:           return jsonify({"ok": False, "msg": "count must be > 0"})

    lic = License.query.filter_by(key=key).first()
    if not lic: return jsonify({"ok": False, "msg": "License not found"})
    if lic.mac_id != mac: return jsonify({"ok": False, "msg": "MAC mismatch or not bound"})

    lic.credit += cnt
    lic.updated_at = datetime.utcnow()
    # Log the refund action
    log = ActivityLog(
        license_id=lic.id,
        action="refund",
        char_count=cnt,
        details=f"Refunded {cnt} credits for key {key}"
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True, "refunded": cnt, "credit": lic.credit})

def _api_next_api_key():
    k = ApiKey.query.filter_by(status="active").first()
    if not k: return jsonify({"ok": False, "msg": "No active API keys"})
    return jsonify({"ok": True, "api_key": k.api_key, "status": "active"})

def _api_deactivate_api_key(req):
    api_key = (req.get("api_key") or "").strip()
    if not api_key: return jsonify({"ok": False, "msg": "api_key required"})
    k = ApiKey.query.filter_by(api_key=api_key).first()
    if not k: return jsonify({"ok": False, "msg": "API key not found"})
    k.status = "inactive"
    db.session.commit()
    return jsonify({"ok": True, "status": "inactive"})

def _api_get_voices():
    vs = Voice.query.filter_by(active=True).all()
    out = [{"name": v.name, "voice_id": v.voice_id} for v in vs]
    return jsonify({"ok": True, "voices": out})

def _api_get_config():
    c = Config.query.first()
    if not c: return jsonify({"ok": False, "msg": "Config missing"})
    links = []
    raw = (c.update_links or "").strip()
    if raw:
        if raw.lstrip().startswith("["):
            try:
                links = json.loads(raw)
            except Exception:
                links = []
        else:
            links = [s.strip() for s in raw.split(",") if s.strip()]
    return jsonify({"ok": True, "config": {
        "latest_version": c.latest_version,
        "force_update": c.force_update,
        "maintenance": c.maintenance,
        "maintenance_message": c.maintenance_message,
        "update_description": c.update_description,
        "update_links": links
    }})

# ==================================================
# ============== ADMIN REST (/admin_api) ===========
# ==================================================

# ---------- Licenses ----------
@app.route("/admin_api/licenses", methods=["GET"])
def adm_list_licenses():
    q = (request.args.get("q") or "").strip()
    query = License.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(License.key.ilike(like), License.mac_id.ilike(like))
        )
    items = query.order_by(License.id.desc()).all()
    return jsonify([{
        "id": x.id, "key": x.key, "mac_id": x.mac_id or "",
        "credit": x.credit, "active": x.active,
        "created_at": x.created_at.isoformat() if x.created_at else "",
        "updated_at": x.updated_at.isoformat() if x.updated_at else ""
    } for x in items])

@app.route("/admin_api/licenses", methods=["POST"])
def adm_create_license():
    data = request.get_json(force=True, silent=True) or {}
    key = (data.get("key") or "").strip()
    if not key: return jsonify({"ok": False, "msg": "key is required"}), 400
    if License.query.filter_by(key=key).first():
        return jsonify({"ok": False, "msg": "key already exists"}), 409
    lic = License(
        key=key,
        mac_id=(data.get("mac_id") or "").strip() or None,
        credit=int(data.get("credit") or 0),
        active=bool(data.get("active")) if data.get("active") is not None else True
    )
    db.session.add(lic)
    db.session.commit()
    return jsonify({"ok": True, "id": lic.id})

@app.route("/admin_api/licenses/<int:lid>", methods=["PUT"])
def adm_update_license(lid):
    lic = License.query.get(lid)
    if not lic: return jsonify({"ok": False, "msg": "not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    if "key" in data:
        new_key = (data.get("key") or "").strip()
        if not new_key: return jsonify({"ok": False, "msg": "key cannot be empty"}), 400
        exists = License.query.filter(License.key == new_key, License.id != lid).first()
        if exists: return jsonify({"ok": False, "msg": "key already exists"}), 409
        lic.key = new_key
    if "mac_id" in data: lic.mac_id = (data.get("mac_id") or "").strip() or None
    if "credit" in data: lic.credit = max(0, int(data.get("credit") or 0))
    if "active" in data: lic.active = bool(data.get("active"))
    lic.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/licenses/<int:lid>", methods=["DELETE"])
def adm_delete_license(lid):
    lic = License.query.get(lid)
    if not lic: return jsonify({"ok": False, "msg": "not found"}), 404
    db.session.delete(lic)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/licenses/<int:lid>/toggle", methods=["POST"])
def adm_toggle_license(lid):
    lic = License.query.get(lid)
    if not lic: return jsonify({"ok": False, "msg": "not found"}), 404
    lic.active = not lic.active
    lic.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "active": lic.active})

@app.route("/admin_api/licenses/<int:lid>/credit", methods=["POST"])
def adm_adjust_credit(lid):
    lic = License.query.get(lid)
    if not lic: return jsonify({"ok": False, "msg": "not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    delta = int(data.get("delta") or 0)
    lic.credit = max(0, (lic.credit or 0) + delta)
    lic.updated_at = datetime.utcnow()
    # Log the credit adjustment
    log = ActivityLog(
        license_id=lic.id,
        action="adjust_credit",
        char_count=delta,
        details=f"Adjusted credit by {delta} for key {lic.key}"
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True, "credit": lic.credit})

# ---------- ApiKeys ----------
@app.route("/admin_api/apikeys", methods=["GET"])
def adm_list_apikeys():
    items = ApiKey.query.order_by(ApiKey.id.desc()).all()
    return jsonify([{"id": x.id, "api_key": x.api_key, "status": x.status} for x in items])

@app.route("/admin_api/apikeys", methods=["POST"])
def adm_create_apikey():
    data = request.get_json(force=True, silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    status = (data.get("status") or "active").strip() or "active"
    if not api_key: return jsonify({"ok": False, "msg": "api_key required"}), 400
    if ApiKey.query.filter_by(api_key=api_key).first():
        return jsonify({"ok": False, "msg": "api_key already exists"}), 409
    k = ApiKey(api_key=api_key, status=status)
    db.session.add(k)
    db.session.commit()
    return jsonify({"ok": True, "id": k.id})

@app.route("/admin_api/apikeys/<int:kid>", methods=["PUT"])
def adm_update_apikey(kid):
    k = ApiKey.query.get(kid)
    if not k: return jsonify({"ok": False, "msg": "not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    if "api_key" in data:
        new_val = (data.get("api_key") or "").strip()
        if not new_val: return jsonify({"ok": False, "msg": "api_key cannot be empty"}), 400
        exists = ApiKey.query.filter(ApiKey.api_key == new_val, ApiKey.id != kid).first()
        if exists: return jsonify({"ok": False, "msg": "api_key already exists"}), 409
        k.api_key = new_val
    if "status" in data:
        k.status = (data.get("status") or "").strip() or k.status
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/apikeys/<int:kid>", methods=["DELETE"])
def adm_delete_apikey(kid):
    k = ApiKey.query.get(kid)
    if not k: return jsonify({"ok": False, "msg": "not found"}), 404
    db.session.delete(k)
    db.session.commit()
    return jsonify({"ok": True})

# ---------- Voices ----------
@app.route("/admin_api/voices", methods=["GET"])
def adm_list_voices():
    items = Voice.query.order_by(Voice.id.desc()).all()
    return jsonify([{"id": x.id, "name": x.name, "voice_id": x.voice_id, "active": x.active} for x in items])

@app.route("/admin_api/voices", methods=["POST"])
def adm_create_voice():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    voice_id = (data.get("voice_id") or "").strip()
    active = bool(data.get("active")) if data.get("active") is not None else True
    if not name or not voice_id:
        return jsonify({"ok": False, "msg": "name and voice_id required"}), 400
    v = Voice(name=name, voice_id=voice_id, active=active)
    db.session.add(v)
    db.session.commit()
    return jsonify({"ok": True, "id": v.id})

@app.route("/admin_api/voices/upload", methods=["POST"])
def adm_upload_voices():
    if 'file' not in request.files:
        return jsonify({"ok": False, "msg": "No file provided"}), 400
    file = request.files['file']
    if not file.filename.endswith('.txt'):
        return jsonify({"ok": False, "msg": "File must be .txt"}), 400
    
    try:
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        added = 0
        for line in lines:
            line = line.strip()
            if not line or ':' not in line:
                continue
            name, voice_id = line.split(':', 1)
            name = name.strip()
            voice_id = voice_id.strip()
            if not name or not voice_id:
                continue
            if Voice.query.filter_by(voice_id=voice_id).first():
                continue  # Skip if voice_id already exists
            v = Voice(name=name, voice_id=voice_id, active=True)
            db.session.add(v)
            added += 1
        db.session.commit()
        return jsonify({"ok": True, "added": added, "msg": f"Added {added} voices"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error processing file: {str(e)}"}), 400

@app.route("/admin_api/voices/<int:vid>", methods=["PUT"])
def adm_update_voice(vid):
    v = Voice.query.get(vid)
    if not v: return jsonify({"ok": False, "msg": "not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    if "name" in data: v.name = (data.get("name") or "").strip() or v.name
    if "voice_id" in data: v.voice_id = (data.get("voice_id") or "").strip() or v.voice_id
    if "active" in data: v.active = bool(data.get("active"))
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/admin_api/voices/<int:vid>", methods=["DELETE"])
def adm_delete_voice(vid):
    v = Voice.query.get(vid)
    if not v: return jsonify({"ok": False, "msg": "not found"}), 404
    db.session.delete(v)
    db.session.commit()
    return jsonify({"ok": True})

# ---------- Activity Logs ----------
@app.route("/admin_api/logs", methods=["GET"])
def adm_list_logs():
    query = ActivityLog.query.order_by(ActivityLog.created_at.desc())
    q = (request.args.get("q") or "").strip()
    min_chars = request.args.get("min_chars", type=int)
    max_chars = request.args.get("max_chars", type=int)
    action = (request.args.get("action") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    if q:
        like = f"%{q}%"
        query = query.join(License).filter(
            db.or_(License.key.ilike(like), License.mac_id.ilike(like))
        )
    if min_chars is not None:
        query = query.filter(ActivityLog.char_count >= min_chars)
    if max_chars is not None:
        query = query.filter(ActivityLog.char_count <= max_chars)
    if action:
        query = query.filter(ActivityLog.action == action)
    if date_from:
        try:
            query = query.filter(ActivityLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            return jsonify({"ok": False, "msg": "Invalid date_from format"}), 400
    if date_to:
        try:
            query = query.filter(ActivityLog.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            return jsonify({"ok": False, "msg": "Invalid date_to format"}), 400

    items = query.limit(100).all()  # Limit to last 100 logs
    return jsonify([{
        "id": x.id,
        "license_id": x.license_id,
        "action": x.action,
        "char_count": x.char_count,
        "details": x.details,
        "created_at": x.created_at.isoformat() if x.created_at else ""
    } for x in items])

# ---------- Backup ----------
@app.route("/admin_api/backup", methods=["GET"])
def adm_backup():
    try:
        c = Config.query.first()
        backup = {
            "licenses": [{
                "id": x.id, "key": x.key, "mac_id": x.mac_id or "",
                "credit": x.credit, "active": x.active,
                "created_at": x.created_at.isoformat() if x.created_at else "",
                "updated_at": x.updated_at.isoformat() if x.created_at else ""
            } for x in License.query.all()],
            "apikeys": [{"id": x.id, "api_key": x.api_key, "status": x.status} for x in ApiKey.query.all()],
            "voices": [{"id": x.id, "name": x.name, "voice_id": x.voice_id, "active": x.active} for x in Voice.query.all()],
            "config": {
                "latest_version": c.latest_version,
                "force_update": c.force_update,
                "maintenance": c.maintenance,
                "maintenance_message": c.maintenance_message,
                "update_description": c.update_description,
                "update_links": c.update_links
            } if c else {}
        }
        output = BytesIO()
        output.write(json.dumps(backup, indent=2, ensure_ascii=False).encode('utf-8'))
        output.seek(0)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return send_file(
            output,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'amulet_backup_{timestamp}.json'
        )
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Backup error: {str(e)}"}), 500

@app.route("/admin_api/backup/licenses", methods=["GET"])
def adm_backup_licenses():
    try:
        backup = {
            "licenses": [{
                "id": x.id, "key": x.key, "mac_id": x.mac_id or "",
                "credit": x.credit, "active": x.active,
                "created_at": x.created_at.isoformat() if x.created_at else "",
                "updated_at": x.updated_at.isoformat() if x.updated_at else ""
            } for x in License.query.all()]
        }
        output = BytesIO()
        output.write(json.dumps(backup, indent=2, ensure_ascii=False).encode('utf-8'))
        output.seek(0)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return send_file(
            output,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'amulet_licenses_backup_{timestamp}.json'
        )
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Backup error: {str(e)}"}), 500

# ---------- Config ----------
@app.route("/admin_api/config", methods=["GET"])
def adm_get_config():
    c = Config.query.first()
    if not c:
        return jsonify({"ok": False, "msg": "Config missing"}), 404
    return jsonify({
        "latest_version": c.latest_version,
        "force_update": c.force_update,
        "maintenance": c.maintenance,
        "maintenance_message": c.maintenance_message,
        "update_description": c.update_description,
        "update_links": c.update_links
    })

@app.route("/admin_api/config", methods=["PUT"])
def adm_update_config():
    c = Config.query.first()
    if not c:
        c = Config()
        db.session.add(c)
    data = request.get_json(force=True, silent=True) or {}
    if "latest_version" in data: c.latest_version = str(data.get("latest_version") or "")
    if "force_update" in data:    c.force_update = bool(data.get("force_update"))
    if "maintenance" in data:     c.maintenance = bool(data.get("maintenance"))
    if "maintenance_message" in data: c.maintenance_message = str(data.get("maintenance_message") or "")
    if "update_description" in data: c.update_description = str(data.get("update_description") or "")
    if "update_links" in data:    c.update_links = str(data.get("update_links") or "")
    db.session.commit()
    return jsonify({"ok": True})

# ==================================================
# ================ ADMIN UI PAGES ==================
# ==================================================
@app.route("/")
@app.route("/admin")
def admin_page():
    return send_from_directory('.', 'admin.html')

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3030)), debug=True)