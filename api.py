from flask import Blueprint, request, jsonify
from models import db, License, ApiKey, Config, ActivityLog

api_bp = Blueprint("api_bp", __name__)

@api_bp.post("/api")
def api_dispatch():
    data = request.get_json(force=True, silent=True) or {}
    action = (data.get("action") or "").strip()

    if action == "get_config":
        c = Config.query.first()
        if not c: return jsonify({})
        return jsonify({
            "latest_version": c.latest_version,
            "force_update": c.force_update,
            "maintenance": c.maintenance,
            "maintenance_message": c.maintenance_message,
            "update_description": c.update_description,
            "update_links": c.update_links
        })

    elif action == "check":
        key = (data.get("key") or "").strip()
        mac = (data.get("mac") or "").strip()
        lic = License.query.filter_by(key=key).first()
        if not lic or not lic.active:
            return jsonify({"ok": False, "error": "invalid_or_inactive"}), 403
        if lic.mac_id and lic.mac_id != mac:
            return jsonify({"ok": False, "error": "mac_mismatch"}), 403
        return jsonify({"ok": True, "credit": lic.credit})

    elif action == "debit":
        key = (data.get("key") or "").strip()
        count = int(data.get("count") or 0)
        model = (data.get("model") or "").strip()
        lic = License.query.filter_by(key=key, active=True).first()
        if not lic:
            return jsonify({"ok": False, "error": "no_license"}), 403
        if lic.credit < count:
            return jsonify({"ok": False, "error": "insufficient"}), 402
        lic.credit -= count; db.session.commit()
        db.session.add(ActivityLog(license_id=lic.id, action="debit",
                                   char_count=count, details=model))
        db.session.commit()
        return jsonify({"ok": True, "credit": lic.credit})

    elif action == "refund":
        key = (data.get("key") or "").strip()
        count = int(data.get("count") or 0)
        reason = (data.get("reason") or "").strip()
        lic = License.query.filter_by(key=key).first()
        if not lic:
            return jsonify({"ok": False, "error": "no_license"}), 404
        lic.credit += count; db.session.commit()
        db.session.add(ActivityLog(license_id=lic.id, action="refund",
                                   char_count=count, details=reason))
        db.session.commit()
        return jsonify({"ok": True, "credit": lic.credit})

    elif action == "next_api_key":
        ak = ApiKey.query.filter_by(status="active").order_by(ApiKey.id.asc()).first()
        if not ak:
            return jsonify({"ok": False, "error": "no_active_keys"}), 404
        return jsonify({"ok": True, "api_key": ak.api_key})

    elif action == "release_api_key":
        return jsonify({"ok": True})

    elif action == "deactivate_api_key":
        k = (data.get("api_key") or "").strip()
        ak = ApiKey.query.filter_by(api_key=k).first()
        if not ak:
            return jsonify({"ok": False, "error": "not_found"}), 404
        ak.status = "inactive"; db.session.commit()
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "unknown_action"}), 400