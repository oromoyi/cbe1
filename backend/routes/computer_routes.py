from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, Computer, Branch
from utils import roles_required, audit

bp = Blueprint("computers", __name__, url_prefix="/api/computers")


@bp.get("")
@jwt_required()
def list_computers():
    q = Computer.query
    branch_id = request.args.get("branch_id")
    status = request.args.get("status")
    search = request.args.get("search")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if status:
        q = q.filter_by(status=status)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Computer.asset_number.ilike(like), Computer.hostname.ilike(like)))
    return jsonify([c.to_dict() for c in q.order_by(Computer.asset_number).all()])


@bp.get("/<int:comp_id>")
@jwt_required()
def get_computer(comp_id):
    return jsonify(Computer.query.get_or_404(comp_id).to_dict())


@bp.post("")
@roles_required("district_admin", "technician")
def create_computer():
    data = request.get_json(force=True) or {}
    if not data.get("asset_number") or not data.get("branch_id"):
        return jsonify({"error": "'asset_number' and 'branch_id' are required"}), 400
    if Computer.query.filter_by(asset_number=data["asset_number"]).first():
        return jsonify({"error": "Asset number already exists"}), 409
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    c = Computer(
        asset_number=data["asset_number"],
        hostname=data.get("hostname"),
        branch_id=data["branch_id"],
        department=data.get("department"),
        employee_id=data.get("employee_id"),
        operating_system=data.get("operating_system"),
        ram=data.get("ram"),
        storage=data.get("storage"),
        processor=data.get("processor"),
        ip_address=data.get("ip_address"),
        mac_address=data.get("mac_address"),
        antivirus_status=data.get("antivirus_status", "PROTECTED"),
        status=data.get("status", "WORKING"),
    )
    db.session.add(c)
    db.session.commit()
    audit("Computer registered", f"Registered computer {c.asset_number}")
    return jsonify(c.to_dict()), 201


@bp.put("/<int:comp_id>")
@roles_required("district_admin", "technician")
def update_computer(comp_id):
    c = Computer.query.get_or_404(comp_id)
    data = request.get_json(force=True) or {}
    for field in [
        "hostname", "department", "employee_id", "operating_system", "ram", "storage",
        "processor", "ip_address", "mac_address", "antivirus_status", "status",
        "last_maintenance_date",
    ]:
        if field in data:
            setattr(c, field, data[field])
    db.session.commit()
    audit("Computer updated", f"Updated computer {c.asset_number} -> {c.status}")
    return jsonify(c.to_dict())


@bp.delete("/<int:comp_id>")
@roles_required("district_admin")
def delete_computer(comp_id):
    c = Computer.query.get_or_404(comp_id)
    asset = c.asset_number
    db.session.delete(c)
    db.session.commit()
    audit("Computer deleted", f"Deleted computer {asset}")
    return jsonify({"message": "Computer deleted"})
