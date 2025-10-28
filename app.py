import os
from flask import Flask, jsonify, request, send_from_directory, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from functools import wraps
from datetime import datetime
import io
import json

# ---------------- CONFIG ----------------
app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///amulet.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("SECRET_KEY", "amulet_secret")

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    mac_id = db.Column(db.String(128))
    credit = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(128), unique=True)
    status = db.Column(db.String(64), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Voice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    voice_id = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=True)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(64))
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.Text)
    update_description = db.Column(db.Text)
    update_links = db.Column(db.Text)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(128))
    action = db.Column(db.String(64))
    char_count = db.Column(db.Integer)
    delta = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ---------------- AUTH ----------------
def check_auth(username, password):
    return username == os.getenv("ADMIN_USER", "admin") and password == os.getenv("ADMIN_PASS", "1234")

def authenticate():
    return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Amulet Admin"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ---------------- PUBLIC ROUTES ----------------
@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "✅ Amulet Backend running successfully",
        "database": app.config["SQLALCHEMY_DATABASE_URI"]
    })

@app.route("/healthz")
def healthz():
    return jsonify({"status": "healthy"}), 200

# ---------------- MAIN API ----------------
@app.route("/check", methods=["POST"])
def check_license():
    data = request.get_json()
    key = data.get("key")
    mac = data.get("mac")
    license = License.query.filter_by(key=key).first()
    if not license:
        return jsonify({"status": "error", "message": "License not found"}), 404
    if not license.active:
        return jsonify({"status": "error", "message": "Inactive"}), 403
    if not license.mac_id:
        license.mac_id = mac
        db.session.commit()
    return jsonify({"status": "ok", "credit": license.credit, "active": license.active})

@app.route("/debit", methods=["POST"])
def debit():
    data = request.get_json()
    key, count = data.get("key"), data.get("count", 0)
    license = License.query.filter_by(key=key).first()
    if not license or not license.active:
        return jsonify({"status": "error", "message": "Invalid license"}), 403
    if license.credit < count:
        return jsonify({"status": "error", "message": "Not enough credit"}), 402
    license.credit -= count
    db.session.add(ActivityLog(license_key=key, action="debit", char_count=count, delta=-count))
    db.session.commit()
    return jsonify({"status": "ok", "remaining": license.credit})

@app.route("/refund", methods=["POST"])
def refund():
    data = request.get_json()
    key, count = data.get("key"), data.get("count", 0)
    license = License.query.filter_by(key=key).first()
    if not license:
        return jsonify({"status": "error", "message": "Invalid license"}), 403
    license.credit += count
    db.session.add(ActivityLog(license_key=key, action="refund", char_count=count, delta=count))
    db.session.commit()
    return jsonify({"status": "ok", "credit": license.credit})

@app.route("/get_voices")
def get_voices():
    voices = Voice.query.all()
    return jsonify([{"name": v.name, "voice_id": v.voice_id} for v in voices])

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
@requires_auth
def admin_page():
    return send_from_directory(".", "admin.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# ---------------- ADMIN API ----------------
@app.route("/admin_api/licenses", methods=["GET"])
@requires_auth
def admin_get_licenses():
    return jsonify([l.as_dict() if hasattr(l, 'as_dict') else {
        "id": l.id, "key": l.key, "mac_id": l.mac_id, "credit": l.credit,
        "active": l.active, "created_at": l.created_at, "updated_at": l.updated_at
    } for l in License.query.all()])

@app.route("/admin_api/licenses", methods=["POST"])
@requires_auth
def admin_add_license():
    data = request.get_json()
    l = License(key=data["key"], mac_id=data.get("mac_id"), credit=data.get("credit", 0), active=data.get("active", True))
    db.session.add(l)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/admin_api/licenses/<int:id>", methods=["PUT"])
@requires_auth
def admin_update_license(id):
    data = request.get_json()
    l = License.query.get(id)
    if not l: return jsonify({"error": "not found"}), 404
    l.key = data.get("key", l.key)
    l.mac_id = data.get("mac_id", l.mac_id)
    l.credit = data.get("credit", l.credit)
    l.active = data.get("active", l.active)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/admin_api/licenses/<int:id>", methods=["DELETE"])
@requires_auth
def admin_delete_license(id):
    l = License.query.get(id)
    if not l: return jsonify({"error": "not found"}), 404
    db.session.delete(l)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/admin_api/voices", methods=["GET"])
@requires_auth
def admin_get_voices():
    voices = Voice.query.all()
    return jsonify([{"id": v.id, "name": v.name, "voice_id": v.voice_id, "active": v.active} for v in voices])

@app.route("/admin_api/voices", methods=["POST"])
@requires_auth
def admin_add_voice():
    data = request.get_json()
    v = Voice(name=data["name"], voice_id=data["voice_id"], active=data.get("active", True))
    db.session.add(v)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/admin_api/config", methods=["GET"])
@requires_auth
def admin_get_config():
    c = Config.query.first()
    if not c:
        c = Config()
        db.session.add(c)
        db.session.commit()
    return jsonify({
        "latest_version": c.latest_version,
        "force_update": c.force_update,
        "maintenance": c.maintenance,
        "maintenance_message": c.maintenance_message,
        "update_description": c.update_description,
        "update_links": c.update_links
    })

@app.route("/admin_api/config", methods=["PUT"])
@requires_auth
def admin_save_config():
    data = request.get_json()
    c = Config.query.first()
    if not c:
        c = Config()
        db.session.add(c)
    for field in ["latest_version", "maintenance_message", "update_description", "update_links"]:
        if field in data: setattr(c, field, data[field])
    c.force_update = data.get("force_update", False)
    c.maintenance = data.get("maintenance", False)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/admin_api/backup", methods=["GET"])
@requires_auth
def admin_backup():
    dump = {
        "licenses": [l.__dict__ for l in License.query.all()],
        "apikeys": [a.__dict__ for a in ApiKey.query.all()],
        "voices": [v.__dict__ for v in Voice.query.all()],
        "config": [c.__dict__ for c in Config.query.all()]
    }
    for section in dump.values():
        for r in section:
            r.pop("_sa_instance_state", None)
    buf = io.BytesIO()
    buf.write(json.dumps(dump, indent=2, default=str).encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="application/json", as_attachment=True, download_name="amulet_backup.json")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)