from flask import Flask, jsonify, request, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from functools import wraps
import os

from models import db, License, ApiKey, Voice, Config, ActivityLog

app = Flask(__name__)
CORS(app)

# 🔧 DATABASE CONFIG
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///amulet.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# --- BASIC AUTH ---
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

@app.route("/")
def home():
    return jsonify({"message": "Amulet Backend is running ✅"})

@app.route("/admin")
@requires_auth
def admin():
    return send_from_directory('.', 'admin.html')

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory('.', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)