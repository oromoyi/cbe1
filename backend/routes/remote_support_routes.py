from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, RemoteSupportSession, Branch, Technician
from utils import roles_required, audit

bp = Blueprint("remote_support", __name__, url_prefix="/api/remote-support")


@bp.get("")
@jwt_required()
def list_sessions():
    q = RemoteSupportSession.query
    branch_id = request.args.get("branch_id")
    technician_id = request.args.get("technician_id")
    status = request.args.get("status")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if technician_id:
        q = q.filter_by(technician_id=technician_id)
    if status:
        q = q.filter_by(status=status)
    return jsonify([s.to_dict() for s in q.order_by(RemoteSupportSession.created_at.desc()).all()])


@bp.get("/<int:session_id>")
@jwt_required()
def get_session(session_id):
    return jsonify(RemoteSupportSession.query.get_or_404(session_id).to_dict())


@bp.post("")
@roles_required("district_admin", "technician")
def create_session():
    """
    Create a remote support session RECORD.

    Note (see project requirement #13): this system only records remote
    support activity. Any actual remote-control functionality must be
    performed through a separate, authorized enterprise remote-support
    tool (name recorded via 'remote_tool_used') — this application never
    implements unauthorized remote access, credential collection, or
    hidden control of branch computers.
    """
    data = request.get_json(force=True) or {}
    if not data.get("branch_id") or not data.get("technician_id"):
        return jsonify({"error": "'branch_id' and 'technician_id' are required"}), 400
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404
    if not Technician.query.get(data["technician_id"]):
        return jsonify({"error": "Technician not found"}), 404

    s = RemoteSupportSession(
        ticket_id=data.get("ticket_id"),
        branch_id=data["branch_id"],
        technician_id=data["technician_id"],
        employee_id=data.get("employee_id"),
        scheduled_time=data.get("scheduled_time") or None,
        status=data.get("status", "SCHEDULED"),
        remote_tool_used=data.get("remote_tool_used"),
    )
    db.session.add(s)
    db.session.commit()
    audit("Remote support session scheduled", f"Session {s.id} at branch {s.branch_id}")
    return jsonify(s.to_dict()), 201


@bp.put("/<int:session_id>")
@roles_required("district_admin", "technician")
def update_session(session_id):
    s = RemoteSupportSession.query.get_or_404(session_id)
    data = request.get_json(force=True) or {}

    if data.get("status") == "IN_PROGRESS" and not s.start_time:
        s.start_time = datetime.utcnow()
    if data.get("status") == "COMPLETED" and not s.end_time:
        s.end_time = datetime.utcnow()

    for field in ["scheduled_time", "status", "troubleshooting_steps", "resolution", "remote_tool_used"]:
        if field in data:
            setattr(s, field, data[field])

    db.session.commit()
    audit("Remote support session updated", f"Session {s.id} -> {s.status}")
    return jsonify(s.to_dict())
