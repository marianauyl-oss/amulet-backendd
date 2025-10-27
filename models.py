# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Ініціалізуємо db (буде прив'язаний до app в app.py)
db = SQLAlchemy()

# ========================================
#               МОДЕЛІ
# ========================================
class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(64), index=True)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,
            'created_at': self.created_at.isoformat()
        }

class Voice(db.Model):
    __tablename__ = 'voices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    voice_id = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), default='elevenlabs')
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'voice_id': self.voice_id,
            'provider': self.provider,
            'is_active': self.is_active
        }

class Config(db.Model):
    __tablename__ = 'config'
    
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(20), default="1.0.0")
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.Text, default="")
    update_description = db.Column(db.Text, default="")
    update_links = db.Column(db.Text, default="")

    def to_dict(self):
        return {
            'latest_version': self.latest_version,
            'force_update': self.force_update,
            'maintenance': self.maintenance,
            'maintenance_message': self.maintenance_message,
            'update_description': self.update_description,
            'update_links': self.update_links
        }

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }