from flask import Flask, jsonify, request, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from functools import wraps
from datetime import datetime
import os

# ---------------- CONFIG ----------------
app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///amulet.db")

# Normalize for SQLAlchemy (Render/PostgreSQL fix)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "amulet_secret")

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
from models import License, ApiKey, Voice, Config, ActivityLog

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

# ---------------- ROUTES ----------------

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

# ---------------- API ----------------

@app.route("/check", methods=["POST"])
def check_license():
    data = request.get_json()
    key = data.get("key")
    mac = data.get("mac")

    license = License.query.filter_by(key=key).first()
    if not license:
        return jsonify({"status": "error", "message": "License not found"}), 404

    if not license.active:
        return jsonify({"status": "error", "message": "License inactive"}), 403

    # Link MAC if new
    if not license.mac_id:
        license.mac_id = mac
        db.session.commit()

    return jsonify({
        "status": "ok",
        "key": key,
        "credit": license.credit,
        "active": license.active
    })

@app.route("/debit", methods=["POST"])
def debit():
    data = request.get_json()
    key = data.get("key")
    count = data.get("count", 0)
    model = data.get("model", "default")

    license = License.query.filter_by(key=key).first()
    if not license or not license.active:
        return jsonify({"status": "error", "message": "Invalid license"}), 403

    if license.credit < count:
        return jsonify({"status": "error", "message": "Not enough credit"}), 402

    license.credit -= count
    log = ActivityLog(license_key=key, model=model, char_count=count, delta=-count)
    db.session.add(log)
    db.session.commit()

    return jsonify({"status": "ok", "remaining": license.credit})

@app.route("/refund", methods=["POST"])
def refund():
    data = request.get_json()
    key = data.get("key")
    count = data.get("count", 0)
    model = data.get("model", "default")

    license = License.query.filter_by(key=key).first()
    if not license:
        return jsonify({"status": "error", "message": "Invalid license"}), 403

    license.credit += count
    log = ActivityLog(license_key=key, model=model, char_count=count, delta=count)
    db.session.add(log)
    db.session.commit()

    return jsonify({"status": "ok", "credit": license.credit})

@app.route("/get_voices", methods=["GET"])
def get_voices():
    voices = Voice.query.all()
    return jsonify([{"name": v.name, "voice_id": v.voice_id} for v in voices])

@app.route("/admin")
@requires_auth
def admin_page():
    return send_from_directory(".", "admin.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)