from flask import Blueprint, request, jsonify
from models import db, License, ApiKey, Voice, Config, ActivityLog

api_bp = Blueprint("api_bp", __name__)

def _ok(**kw): return {"ok": True, **kw}
def _err(msg, code=400): return jsonify({"ok": False, "msg": msg}), code

@api_bp.post("/")
def router():
    data = request.get_json(force=True, silent=True) or {}
    action = (data.get("action") or "").strip()

    if action == "get_config":
        c = Config.query.first()
        if not c: c = Config(); db.session.add(c); db.session.commit()
        return jsonify(_ok(config=c.as_dict()))

    if action == "get_voices":
        vs = [v.as_dict() for v in Voice.query.filter_by(active=True).all()]
        return jsonify(_ok(voices=[{"Назва голосу": v["name"], "ID ГОЛОСУ": v["voice_id"]} for v in vs]))

    if action == "check":
        key = (data.get("key") or "").strip()
        mac = (data.get("mac") or "").strip()
        lic = License.query.filter_by(key=key).first()
        if not lic: return _err("license not found", 404)
        if not lic.active: return _err("license inactive", 403)
        if not lic.mac_id:
            lic.mac_id = mac; db.session.commit()
        return jsonify(_ok(credit=lic.credit, active=lic.active))

    if action == "debit":
        key = (data.get("key") or "").strip()
        model = (data.get("model") or "default").strip()
        count = int(data.get("count") or 0)
        lic = License.query.filter_by(key=key).first()
        if not lic or not lic.active: return _err("invalid license", 403)
        if lic.credit < count:       return _err("not enough credit", 402)
        lic.credit -= count
        db.session.add(ActivityLog(license_id=lic.id, action="debit", model=model, char_count=count, delta=-count))
        db.session.commit()
        return jsonify(_ok(debited=count, credit=lic.credit))

    if action == "refund":
        key = (data.get("key") or "").strip()
        model = (data.get("model") or "default").strip()
        count = int(data.get("count") or 0)
        lic = License.query.filter_by(key=key).first()
        if not lic: return _err("invalid license", 403)
        lic.credit += count
        db.session.add(ActivityLog(license_id=lic.id, action="refund", model=model, char_count=count, delta=count, details=data.get("reason") or ""))  # noqa
        db.session.commit()
        return jsonify(_ok(credit=lic.credit))

    if action == "next_api_key":
        ak = ApiKey.query.filter_by(status="active").order_by(ApiKey.id.desc()).first()
        if not ak: return _err("no active api keys", 404)
        return jsonify(_ok(api_key=ak.api_key))

    if action == "release_api_key":
        # no-op (сумісність із клієнтом)
        return jsonify(_ok(released=True))

    if action == "deactivate_api_key":
        k = (data.get("api_key") or "").strip()
        ak = ApiKey.query.filter_by(api_key=k).first()
        if not ak: return _err("api key not found", 404)
        ak.status = "inactive"; db.session.commit()
        return jsonify(_ok(status="inactive"))

    return _err("unknown action", 400)