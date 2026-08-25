import json
from flask import Blueprint, request, jsonify

from models import db, AppSetting
from utils import roles_required, audit

bp = Blueprint("settings", __name__, url_prefix="/api/settings")

DEFAULTS = {
    "organization_name": "Commercial Bank of Ethiopia",
    "district_name": "District IT Office",
    "district_code": "CBE-DIT",
    "region": "Oromia",
    "office_address": "",
    "support_email": "it-support@example.com",
    "support_phone": "",
    "timezone": "Africa/Addis_Ababa",
    "currency": "ETB",
    "default_ticket_priority": "MEDIUM",
    "maintenance_interval_days": 90,
    "simulation_mode": True,
}


def settings_dict():
    result = dict(DEFAULTS)
    for item in AppSetting.query.all():
        try:
            result[item.key] = json.loads(item.value)
        except (TypeError, json.JSONDecodeError):
            result[item.key] = item.value
    return result


@bp.get("")
@roles_required("district_admin")
def get_settings():
    return jsonify(settings_dict())


@bp.put("")
@roles_required("district_admin")
def update_settings():
    data = request.get_json(force=True) or {}
    allowed = set(DEFAULTS)
    unknown = sorted(set(data) - allowed)
    if unknown:
        return jsonify({"error": f"Unsupported setting: {unknown[0]}"}), 400
    for key, value in data.items():
        item = AppSetting.query.filter_by(key=key).first()
        serialized = json.dumps(value)
        if item:
            item.value = serialized
        else:
            db.session.add(AppSetting(key=key, value=serialized))
    db.session.commit()
    audit("Settings updated", "Updated CBE district application settings")
    return jsonify(settings_dict())
