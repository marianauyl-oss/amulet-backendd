from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timedelta
from sqlalchemy import or_
from models import db, License, ApiKey, Voice, Config, ActivityLog

admin_bp = Blueprint("admin_bp", __name__)

def parse_date(dstr, end=False):
    if not dstr: return None
    try:
        dt = datetime.strptime(dstr, "%Y-%m-%d")
        if end: dt = dt + timedelta(days=1)
        return dt
    except Exception:
        return None

# ---- LICENSES ----
@admin_bp.get("/licenses")
def list_licenses():
    q = (request.args.get("q") or "").strip()
    min_credit = request.args.get("min_credit", type=int)
    max_credit = request.args.get("max_credit", type=int)
    active = request.args.get("active")
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"), end=True)

    qry = License.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(License.key.ilike(like), License.mac_id.ilike(like)))
    if min_credit is not None: qry = qry.filter(License.credit >= min_credit)
    if max_credit is not None: qry = qry.filter(License.credit <= max_credit)
    if active in ("true","false"): qry = qry.filter(License.active == (active == "true"))
    if date_from: qry = qry.filter(License.created_at >= date_from)
    if date_to:   qry = qry.filter(License.created_at < date_to)

    rows = qry.order_by(License.id.desc()).all()
    return jsonify([{
        "id": x.id, "key": x.key, "mac_id": x.mac_id, "credit": x.credit,
        "active": x.active,
        "created_at": x.created_at.isoformat() if x.created_at else None,
        "updated_at": x.updated_at.isoformat() if x.updated_at else None
    } for x in rows])

@admin_bp.post("/licenses")
def create_license():
    data = request.get_json(force=True)
    lic = License(
        key=(data.get("key") or "").strip(),
        mac_id=(data.get("mac_id") or "").strip() or None,
        credit=int(data.get("credit") or 0),
        active=bool(data.get("active"))
    )
    db.session.add(lic); db.session.commit()
    return jsonify({"id": lic.id}), 201

@admin_bp.put("/licenses/<int:lic_id>")
def update_license(lic_id):
    lic = License.query.get_or_404(lic_id)
    data = request.get_json(force=True)
    if "key" in data: lic.key = (data.get("key") or "").strip()
    if "mac_id" in data: lic.mac_id = (data.get("mac_id") or "").strip() or None
    if "credit" in data: lic.credit = int(data.get("credit") or 0)
    if "active" in data: lic.active = bool(data.get("active"))
    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.delete("/licenses/<int:lic_id>")
def delete_license(lic_id):
    lic = License.query.get_or_404(lic_id)
    db.session.delete(lic); db.session.commit()
    return jsonify({"ok": True})

@admin_bp.post("/licenses/<int:lic_id>/toggle")
def toggle_license(lic_id):
    lic = License.query.get_or_404(lic_id)
    lic.active = not lic.active
    db.session.commit()
    return jsonify({"active": lic.active})

@admin_bp.post("/licenses/<int:lic_id>/credit")
def adjust_credit(lic_id):
    lic = License.query.get_or_404(lic_id)
    data = request.get_json(force=True)
    delta = int(data.get("delta") or 0)
    lic.credit += delta
    db.session.commit()
    db.session.add(ActivityLog(
        license_id=lic.id, action="adjust_credit",
        char_count=abs(delta), details=f"delta={delta}"
    ))
    db.session.commit()
    return jsonify({"credit": lic.credit})

# ---- API KEYS ----
@admin_bp.get("/apikeys")
def list_apikeys():
    rows = ApiKey.query.order_by(ApiKey.id.desc()).all()
    return jsonify([{
        "id": x.id, "api_key": x.api_key, "status": x.status,
        "created_at": x.created_at.isoformat() if x.created_at else None
    } for x in rows])

@admin_bp.post("/apikeys")
def create_apikey():
    data = request.get_json(force=True)
    ak = ApiKey(api_key=(data.get("api_key") or "").strip(),
                status=(data.get("status") or "active"))
    db.session.add(ak); db.session.commit()
    return jsonify({"id": ak.id}), 201

@admin_bp.put("/apikeys/<int:ak_id>")
def update_apikey(ak_id):
    ak = ApiKey.query.get_or_404(ak_id)
    data = request.get_json(force=True)
    if "api_key" in data: ak.api_key = (data.get("api_key") or "").strip()
    if "status" in data: ak.status = (data.get("status") or "active")
    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.delete("/apikeys/<int:ak_id>")
def delete_apikey(ak_id):
    ak = ApiKey.query.get_or_404(ak_id)
    db.session.delete(ak); db.session.commit()
    return jsonify({"ok": True})

# ---- VOICES ----
@admin_bp.get("/voices")
def list_voices():
    rows = Voice.query.order_by(Voice.id.desc()).all()
    return jsonify([{
        "id": x.id, "name": x.name, "voice_id": x.voice_id, "active": x.active
    } for x in rows])

@admin_bp.post("/voices")
def create_voice():
    data = request.get_json(force=True)
    v = Voice(
        name=(data.get("name") or "").strip(),
        voice_id=(data.get("voice_id") or "").strip(),
        active=bool(data.get("active"))
    )
    db.session.add(v); db.session.commit()
    return jsonify({"id": v.id}), 201

@admin_bp.put("/voices/<int:v_id>")
def update_voice(v_id):
    v = Voice.query.get_or_404(v_id)
    data = request.get_json(force=True)
    if "name" in data: v.name = (data.get("name") or "").strip()
    if "voice_id" in data: v.voice_id = (data.get("voice_id") or "").strip()
    if "active" in data: v.active = bool(data.get("active"))
    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.delete("/voices/<int:v_id>")
def delete_voice(v_id):
    v = Voice.query.get_or_404(v_id)
    db.session.delete(v); db.session.commit()
    return jsonify({"ok": True})

@admin_bp.post("/voices/upload")
def upload_voices():
    if 'file' not in request.files:
        return jsonify({"msg": "no file"}), 400
    f = request.files['file']
    text = f.read().decode('utf-8', errors='ignore')
    added = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or ":" not in line: continue
        name, voice_id = line.split(":", 1)
        name = name.strip(); voice_id = voice_id.strip()
        if not name or not voice_id: continue
        exists = Voice.query.filter_by(name=name, voice_id=voice_id).first()
        if exists: continue
        v = Voice(name=name, voice_id=voice_id, active=True)
        db.session.add(v); added += 1
    db.session.commit()
    return jsonify({"added": added})

# ---- LOGS ----
@admin_bp.get("/logs")
def list_logs():
    q = (request.args.get("q") or "").strip()
    min_chars = request.args.get("min_chars", type=int)
    max_chars = request.args.get("max_chars", type=int)
    action = (request.args.get("action") or "").strip()
    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"), end=True)

    qry = ActivityLog.query
    if q: qry = qry.filter(ActivityLog.details.ilike(f"%{q}%"))
    if min_chars is not None: qry = qry.filter(ActivityLog.char_count >= min_chars)
    if max_chars is not None: qry = qry.filter(ActivityLog.char_count <= max_chars)
    if action: qry = qry.filter(ActivityLog.action == action)
    if date_from: qry = qry.filter(ActivityLog.created_at >= date_from)
    if date_to: qry = qry.filter(ActivityLog.created_at < date_to)

    rows = qry.order_by(ActivityLog.id.desc()).all()
    return jsonify([{
        "id": x.id, "license_id": x.license_id, "action": x.action,
        "char_count": x.char_count, "details": x.details,
        "created_at": x.created_at.isoformat() if x.created_at else None
    } for x in rows])

# ---- CONFIG ----
@admin_bp.get("/config")
def get_config():
    c = Config.query.first()
    if not c:
        c = Config(); db.session.add(c); db.session.commit()
    return jsonify({
        "latest_version": c.latest_version,
        "force_update": c.force_update,
        "maintenance": c.maintenance,
        "maintenance_message": c.maintenance_message,
        "update_description": c.update_description,
        "update_links": c.update_links
    })

@admin_bp.put("/config")
def save_config():
    data = request.get_json(force=True)
    c = Config.query.first() or Config()
    c.latest_version = (data.get("latest_version") or "").strip()
    c.force_update = bool(data.get("force_update"))
    c.maintenance = bool(data.get("maintenance"))
    c.maintenance_message = data.get("maintenance_message") or ""
    c.update_description = data.get("update_description") or ""
    c.update_links = data.get("update_links") or ""
    db.session.add(c); db.session.commit()
    return jsonify({"ok": True})

# ---- BACKUPS ----
@admin_bp.get("/backup")
def full_backup():
    data = {
        "licenses": [{
            "id": x.id, "key": x.key, "mac_id": x.mac_id,
            "credit": x.credit, "active": x.active,
            "created_at": x.created_at.isoformat() if x.created_at else None,
            "updated_at": x.updated_at.isoformat() if x.updated_at else None
        } for x in License.query.all()],
        "api_keys": [{
            "id": x.id, "api_key": x.api_key, "status": x.status,
            "created_at": x.created_at.isoformat() if x.created_at else None
        } for x in ApiKey.query.all()],
        "voices": [{
            "id": x.id, "name": x.name, "voice_id": x.voice_id, "active": x.active
        } for x in Voice.query.all()],
        "config": (lambda c: {
            "latest_version": c.latest_version,
            "force_update": c.force_update,
            "maintenance": c.maintenance,
            "maintenance_message": c.maintenance_message,
            "update_description": c.update_description,
            "update_links": c.update_links
        })(Config.query.first() or Config()),
        "logs": [{
            "id": x.id, "license_id": x.license_id, "action": x.action,
            "char_count": x.char_count, "details": x.details,
            "created_at": x.created_at.isoformat() if x.created_at else None
        } for x in ActivityLog.query.all()],
    }
    import json
    buf = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        buf, mimetype="application/json",
        headers={"Content-Disposition": 'attachment; filename="amulet_backup.json"'}
    )

@admin_bp.get("/backup/licenses")
def backup_licenses():
    data = [{
        "id": x.id, "key": x.key, "mac_id": x.mac_id, "credit": x.credit,
        "active": x.active,
        "created_at": x.created_at.isoformat() if x.created_at else None,
        "updated_at": x.updated_at.isoformat() if x.updated_at else None
    } for x in License.query.all()]
    import json
    buf = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        buf, mimetype="application/json",
        headers={"Content-Disposition": 'attachment; filename="amulet_licenses_backup.json"'}
    )