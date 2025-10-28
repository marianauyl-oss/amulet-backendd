import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from models import db
from admin_api import admin_api
from api import api_bp

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ---- DATABASE URL normalize (Railway/Render) ----
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///amulet.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "amulet_secret")

db.init_app(app)
with app.app_context():
    db.create_all()

# ---- Health / Root ----
@app.get("/")
def index():
    return jsonify({"ok": True, "message": "Amulet Backend running", "database": app.config["SQLALCHEMY_DATABASE_URI"]})

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})

# ---- Admin page ----
@app.get("/admin")
def admin_page():
    # Саму сторінку захищає блюпринт (через 401 на API-виклики) — сторінка віддається, але дані без Basic Auth не прийдуть.
    return send_from_directory("static", "admin.html")

# ---- Blueprints ----
app.register_blueprint(admin_api, url_prefix="/admin/api")
app.register_blueprint(api_bp,    url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))