# app.py
import os
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__, static_folder='.')
CORS(app)

# --- БАЗА ДАНИХ ---
if os.getenv('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    os.makedirs('instance', exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/db.sqlite'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛІ ---
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.String(64))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(20), default="1.0.0")
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)

# --- ІНІЦІАЛІЗАЦІЯ ---
with app.app_context():
    db.create_all()
    if not Config.query.first():
        db.session.add(Config())
        db.session.commit()

# --- МАРШРУТИ ---
@app.route('/')
def index():
    return send_file('admin.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/config', methods=['GET'])
def get_config():
    config = Config.query.first()
    return jsonify({
        'latest_version': config.latest_version,
        'force_update': config.force_update,
        'maintenance': config.maintenance
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)