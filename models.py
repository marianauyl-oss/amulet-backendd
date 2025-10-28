from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    mac_id = db.Column(db.String(255))
    credit = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id, "key": self.key, "mac_id": self.mac_id,
            "credit": self.credit, "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id, "api_key": self.api_key, "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Voice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    voice_id = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "voice_id": self.voice_id, "active": self.active}

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latest_version = db.Column(db.String(50), default="")
    force_update = db.Column(db.Boolean, default=False)
    maintenance = db.Column(db.Boolean, default=False)
    maintenance_message = db.Column(db.Text, default="")
    update_description = db.Column(db.Text, default="")
    update_links = db.Column(db.Text, default="")  # JSON або CSV

    def as_dict(self):
        return {
            "latest_version": self.latest_version,
            "force_update": self.force_update,
            "maintenance": self.maintenance,
            "maintenance_message": self.maintenance_message,
            "update_description": self.update_description,
            "update_links": self.update_links,
        }

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey("license.id"), nullable=True)
    action = db.Column(db.String(64))  # debit | refund | adjust_credit
    model = db.Column(db.String(255))
    char_count = db.Column(db.Integer, default=0)
    delta = db.Column(db.Integer, default=0)
    details = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id, "license_id": self.license_id, "action": self.action,
            "char_count": self.char_count, "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }