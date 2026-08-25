from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, Incident, Branch
from utils import roles_required, audit, notify, next_code

bp = Blueprint("incidents", __name__, url_prefix="/api/incidents")

INCIDENT_TYPES = ["ATM", "Network", "Computer", "Printer", "Server", "Software", "Security", "Power"]


@bp.get("/types")
@jwt_required()
def types():
    return jsonify(INCIDENT_TYPES)


@bp.get("")
@jwt_required()
def list_incidents():
    q = Incident.query
    branch_id = request.args.get("branch_id")
    status = request.args.get("status")
    category = request.args.get("category")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if status:
        q = q.filter_by(status=status)
    if category:
        q = q.filter_by(category=category)
    return jsonify([i.to_dict() for i in q.order_by(Incident.date_opened.desc()).all()])


@bp.get("/<int:incident_id>")
@jwt_required()
def get_incident(incident_id):
    return jsonify(Incident.query.get_or_404(incident_id).to_dict())


@bp.post("")
@roles_required("district_admin", "technician")
def create_incident():
    data = request.get_json(force=True) or {}
    if not data.get("branch_id") or not data.get("category"):
        return jsonify({"error": "'branch_id' and 'category' are required"}), 400
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    inc = Incident(
        incident_code=next_code("INC", Incident, "incident_code", pad=4, start=2000),
        branch_id=data["branch_id"],
        category=data["category"],
        description=data.get("description"),
        severity=data.get("severity", "MEDIUM"),
        technician_id=data.get("technician_id"),
        status="OPEN",
    )
    db.session.add(inc)
    db.session.commit()
    audit("Incident created", f"{inc.incident_code}: {inc.category}")
    return jsonify(inc.to_dict()), 201


@bp.put("/<int:incident_id>")
@roles_required("district_admin", "technician")
def update_incident(incident_id):
    inc = Incident.query.get_or_404(incident_id)
    data = request.get_json(force=True) or {}
    for field in ["category", "description", "severity", "technician_id", "status", "resolution"]:
        if field in data:
            setattr(inc, field, data[field])
    if data.get("status") == "RESOLVED" and not inc.date_resolved:
        inc.date_resolved = datetime.utcnow()
    db.session.commit()
    audit("Incident updated", f"{inc.incident_code} -> {inc.status}")
    return jsonify(inc.to_dict())
