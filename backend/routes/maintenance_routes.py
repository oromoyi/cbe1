from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, MaintenanceRecord, Branch
from utils import roles_required, audit, notify

bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")


@bp.get("")
@jwt_required()
def list_maintenance():
    q = MaintenanceRecord.query
    branch_id = request.args.get("branch_id")
    maintenance_type = request.args.get("maintenance_type")
    result = request.args.get("result")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if maintenance_type:
        q = q.filter_by(maintenance_type=maintenance_type)
    if result:
        q = q.filter_by(result=result)
    return jsonify([m.to_dict() for m in q.order_by(MaintenanceRecord.created_at.desc()).all()])


@bp.get("/<int:m_id>")
@jwt_required()
def get_maintenance(m_id):
    return jsonify(MaintenanceRecord.query.get_or_404(m_id).to_dict())


@bp.post("")
@roles_required("district_admin", "technician")
def create_maintenance():
    data = request.get_json(force=True) or {}
    if not data.get("branch_id") or not data.get("maintenance_type"):
        return jsonify({"error": "'branch_id' and 'maintenance_type' are required"}), 400
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    m = MaintenanceRecord(
        maintenance_type=data["maintenance_type"],
        asset_id=data.get("asset_id"),
        atm_id=data.get("atm_id"),
        computer_id=data.get("computer_id"),
        branch_id=data["branch_id"],
        technician_id=data.get("technician_id"),
        scheduled_date=data.get("scheduled_date") or None,
        completion_date=data.get("completion_date") or None,
        problem=data.get("problem"),
        checklist=data.get("checklist", {}),
        repair_action=data.get("repair_action"),
        result=data.get("result", "PENDING"),
        notes=data.get("notes"),
    )
    db.session.add(m)
    db.session.commit()

    if m.maintenance_type == "PREVENTIVE" and m.scheduled_date:
        notify(
            title="Scheduled maintenance",
            message=f"Preventive maintenance scheduled for {m.scheduled_date} at {m.branch.name}.",
            type="MAINTENANCE_SCHEDULED",
            related_entity="maintenance_record",
            related_id=m.id,
        )

    audit("Maintenance record created", f"{m.maintenance_type} maintenance at branch {m.branch_id}")
    return jsonify(m.to_dict()), 201


@bp.put("/<int:m_id>")
@roles_required("district_admin", "technician")
def update_maintenance(m_id):
    m = MaintenanceRecord.query.get_or_404(m_id)
    data = request.get_json(force=True) or {}
    for field in [
        "technician_id", "scheduled_date", "completion_date", "problem",
        "checklist", "repair_action", "result", "notes",
    ]:
        if field in data:
            setattr(m, field, data[field])
    db.session.commit()
    audit("Maintenance record updated", f"Maintenance {m.id} -> {m.result}")
    return jsonify(m.to_dict())


@bp.delete("/<int:m_id>")
@roles_required("district_admin")
def delete_maintenance(m_id):
    m = MaintenanceRecord.query.get_or_404(m_id)
    db.session.delete(m)
    db.session.commit()
    audit("Maintenance record deleted", f"Deleted maintenance record {m_id}")
    return jsonify({"message": "Maintenance record deleted"})
