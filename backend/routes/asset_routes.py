from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, Asset, Branch
from utils import roles_required, audit

bp = Blueprint("assets", __name__, url_prefix="/api/assets")

ASSET_TYPES = ["Computer", "Printer", "Scanner", "Router", "Switch", "Access Point", "UPS", "Server", "ATM", "Other"]


@bp.get("/types")
@jwt_required()
def types():
    return jsonify(ASSET_TYPES)


@bp.get("")
@jwt_required()
def list_assets():
    q = Asset.query
    branch_id = request.args.get("branch_id")
    asset_type = request.args.get("asset_type")
    status = request.args.get("status")
    search = request.args.get("search")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if asset_type:
        q = q.filter_by(asset_type=asset_type)
    if status:
        q = q.filter_by(status=status)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Asset.asset_code.ilike(like), Asset.serial_number.ilike(like)))
    return jsonify([a.to_dict() for a in q.order_by(Asset.asset_code).all()])


@bp.get("/<int:asset_id>")
@jwt_required()
def get_asset(asset_id):
    a = Asset.query.get_or_404(asset_id)
    data = a.to_dict()
    data["maintenance_history"] = [m.to_dict() for m in a.maintenance_records]
    return jsonify(data)


@bp.post("")
@roles_required("district_admin", "technician")
def create_asset():
    data = request.get_json(force=True) or {}
    if not data.get("asset_code") or not data.get("branch_id") or not data.get("asset_type"):
        return jsonify({"error": "'asset_code', 'branch_id', and 'asset_type' are required"}), 400
    if Asset.query.filter_by(asset_code=data["asset_code"]).first():
        return jsonify({"error": "Asset code already exists"}), 409
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    a = Asset(
        asset_code=data["asset_code"],
        serial_number=data.get("serial_number"),
        asset_type=data["asset_type"],
        model=data.get("model"),
        branch_id=data["branch_id"],
        assigned_user=data.get("assigned_user"),
        purchase_date=data.get("purchase_date") or None,
        installation_date=data.get("installation_date") or None,
        status=data.get("status", "ACTIVE"),
    )
    db.session.add(a)
    db.session.commit()
    audit("Asset registered", f"Registered asset {a.asset_code} ({a.asset_type})")
    return jsonify(a.to_dict()), 201


@bp.put("/<int:asset_id>")
@roles_required("district_admin", "technician")
def update_asset(asset_id):
    a = Asset.query.get_or_404(asset_id)
    data = request.get_json(force=True) or {}
    for field in [
        "serial_number", "asset_type", "model", "assigned_user",
        "purchase_date", "installation_date", "status",
    ]:
        if field in data:
            setattr(a, field, data[field])
    db.session.commit()
    audit("Asset updated", f"Updated asset {a.asset_code} -> {a.status}")
    return jsonify(a.to_dict())


@bp.delete("/<int:asset_id>")
@roles_required("district_admin")
def delete_asset(asset_id):
    a = Asset.query.get_or_404(asset_id)
    code = a.asset_code
    db.session.delete(a)
    db.session.commit()
    audit("Asset deleted", f"Deleted asset {code}")
    return jsonify({"message": "Asset deleted"})
