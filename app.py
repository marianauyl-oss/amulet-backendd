import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from models import db, License, ApiKey, Voice, Config, ActivityLog
from admin_api import admin_bp
from api import api_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

# =======================
# DATABASE CONFIGURATION
# =======================
db_url = os.getenv('DATABASE_URL')

if db_url:
    # Render може повертати "postgres://" → SQLAlchemy потребує "+psycopg"
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    print(f"✅ Using PostgreSQL database: {db_url}")
else:
    # fallback — локальний SQLite
    os.makedirs('instance', exist_ok=True)
    sqlite_path = 'sqlite:///instance/db.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_path
    print(f"⚙️  Using local SQLite database at {sqlite_path}")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =======================
# CORS CONFIG
# =======================
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/admin_api/*": {"origins": "*"},
})

# =======================
# INIT DATABASE
# =======================
db.init_app(app)

# =======================
# BASIC ADMIN AUTH
# =======================
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', '1234')

def require_admin():
    if not ADMIN_USER or not ADMIN_PASS:
        return  # auth disabled
    auth = request.authorization
    if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASS:
        return jsonify({"error": "auth_required"}), 401, {
            "WWW-Authenticate": 'Basic realm="Amulet Admin"'
        }

@app.before_request
def protect_admin():
    path = request.path or ""
    # public routes
    if path.startswith("/static") or path == "/healthz" or path.startswith("/api"):
        return
    if path.startswith("/admin_api"):
        r = require_admin()
        if r:
            return r

# =======================
# ROUTES
# =======================
@app.route("/")
def index():
    r = require_admin()
    if r:
        return r
    return app.send_static_file("admin.html")

@app.route("/healthz")
def healthz():
    return "ok", 200

# =======================
# BLUEPRINTS
# =======================
app.register_blueprint(admin_bp, url_prefix="/admin_api")
app.register_blueprint(api_bp, url_prefix="/api")

# =======================
# INIT DATABASE TABLES
# =======================
with app.app_context():
    try:
        db.create_all()
        if not Config.query.first():
            db.session.add(Config())
            db.session.commit()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

# =======================
# MAIN
# =======================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)