from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, Branch, ATM, Computer, ITTicket, MaintenanceRecord, NetworkInstallation
from utils import roles_required, audit

bp = Blueprint("branches", __name__, url_prefix="/api/branches")


@bp.get("")
@jwt_required()
def list_branches():
    q = Branch.query
    search = request.args.get("search")
    status = request.args.get("status")
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Branch.name.ilike(like), Branch.branch_code.ilike(like), Branch.location.ilike(like)))
    if status:
        q = q.filter_by(overall_it_status=status)
    branches = q.order_by(Branch.name).all()
    return jsonify([b.to_dict(detailed=True) for b in branches])


@bp.get("/<int:branch_id>")
@jwt_required()
def get_branch(branch_id):
    b = Branch.query.get_or_404(branch_id)
    data = b.to_dict(detailed=True)
    data["atms"] = [a.to_dict() for a in b.atms]
    data["computers"] = [c.to_dict() for c in b.computers]
    data["open_tickets_list"] = [t.to_dict() for t in b.tickets if t.status not in ("RESOLVED", "CLOSED")]
    data["maintenance_history"] = [
        m.to_dict() for m in MaintenanceRecord.query.filter_by(branch_id=branch_id)
        .order_by(MaintenanceRecord.created_at.desc()).limit(20)
    ]
    data["installation_history"] = [i.to_dict() for i in b.installations]
    return jsonify(data)


@bp.post("")
@roles_required("district_admin")
def create_branch():
    data = request.get_json(force=True) or {}
    required = ["branch_code", "name"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400
    if Branch.query.filter_by(branch_code=data["branch_code"]).first():
        return jsonify({"error": "Branch code already exists"}), 409

    b = Branch(
        branch_code=data["branch_code"],
        name=data["name"],
        location=data.get("location"),
        contact_number=data.get("contact_number"),
        branch_manager_name=data.get("branch_manager_name"),
        number_of_computers=data.get("number_of_computers", 0),
        number_of_atms=data.get("number_of_atms", 0),
        network_status=data.get("network_status", "CONNECTED"),
        overall_it_status=data.get("overall_it_status", "GREEN"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    db.session.add(b)
    db.session.commit()
    audit("Branch created", f"Created branch {b.name} ({b.branch_code})")
    return jsonify(b.to_dict()), 201


@bp.put("/<int:branch_id>")
@roles_required("district_admin")
def update_branch(branch_id):
    b = Branch.query.get_or_404(branch_id)
    data = request.get_json(force=True) or {}
    for field in [
        "name", "location", "contact_number", "branch_manager_name",
        "number_of_computers", "number_of_atms", "network_status",
        "overall_it_status", "latitude", "longitude",
    ]:
        if field in data:
            setattr(b, field, data[field])
    db.session.commit()
    audit("Branch updated", f"Updated branch {b.name}")
    return jsonify(b.to_dict())


@bp.delete("/<int:branch_id>")
@roles_required("district_admin")
def delete_branch(branch_id):
    b = Branch.query.get_or_404(branch_id)
    name = b.name
    db.session.delete(b)
    db.session.commit()
    audit("Branch deleted", f"Deleted branch {name}")
    return jsonify({"message": "Branch deleted"})
