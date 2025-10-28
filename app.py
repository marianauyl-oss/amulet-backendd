import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Ініціалізація Flask
app = Flask(__name__)
CORS(app)

# -----------------------------
# Конфігурація бази даних
# -----------------------------
db_url = os.getenv("DATABASE_URL")

# 🔧 Якщо Render дає postgres:// — замінюємо на psycopg3-сумісний URI
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

if not db_url:
    raise RuntimeError("❌ DATABASE_URL не встановлено в середовищі Render.")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Ініціалізація SQLAlchemy
db = SQLAlchemy(app)

# -----------------------------
# Моделі бази даних
# -----------------------------
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    mac_id = db.Column(db.String(128))
    credit = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(128), unique=True, nullable=False)
    status = db.Column(db.String(64), default="active")

class Voice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    voice_id = db.Column(db.String(128))

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(32))
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.String(256))
    update_description = db.Column(db.String(256))
    update_links = db.Column(db.String(256))

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(128))
    model = db.Column(db.String(64))
    char_count = db.Column(db.Integer)
    delta = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)

# -----------------------------
# Ініціалізація бази при запуску
# -----------------------------
with app.app_context():
    db.create_all()
    print("✅ Using PostgreSQL:", db_url)
    import sys
    print("🐍 Python version:", sys.version)

# -----------------------------
# Ендпоінти
# -----------------------------
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

@app.route("/")
def home():
    return jsonify({"message": "Amulet Backend is running ✅"}), 200

# -----------------------------
# Запуск сервера
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)