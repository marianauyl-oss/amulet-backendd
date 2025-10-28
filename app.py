from flask import Flask, jsonify, request, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from functools import wraps
import os
from datetime import datetime

# --- APP INIT ---
app = Flask(__name__)
CORS(app)

# --- DATABASE CONFIG ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///amulet.db")

# Fix old postgres:// URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELS ---
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    mac_id = db.Column(db.String(255))
    credit = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), default="active")

class Voice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    voice_id = db.Column(db.String(255))

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(50))
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.String(255))
    update_description = db.Column(db.String(255))
    update_links = db.Column(db.String(255))

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(255))
    model = db.Column(db.String(255))
    char_count = db.Column(db.Integer)
    delta = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- INIT DB ---
with app.app_context():
    db.create_all()

# --- AUTH HELPERS ---
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

# --- ROUTES ---
@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "✅ Amulet Backend running on Render",
        "db": app.config["SQLALCHEMY_DATABASE_URI"]
    })

@app.route("/admin")
@requires_auth
def admin_panel():
    return send_from_directory(".", "admin.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

@app.route("/healthz")
def health_check():
    return jsonify({"status": "healthy"}), 200

# --- MAIN ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)