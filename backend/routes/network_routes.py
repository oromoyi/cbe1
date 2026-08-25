from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, NetworkInstallation, NetworkEquipment, Branch, CHECKLIST_ITEMS
from utils import roles_required, audit, notify

bp = Blueprint("network", __name__, url_prefix="/api/network-installations")


@bp.get("/checklist-items")
@jwt_required()
def checklist_items():
    return jsonify(CHECKLIST_ITEMS)


@bp.get("")
@jwt_required()
def list_installations():
    q = NetworkInstallation.query
    branch_id = request.args.get("branch_id")
    status = request.args.get("status")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if status:
        q = q.filter_by(status=status)
    items = q.order_by(NetworkInstallation.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])


@bp.get("/<int:inst_id>")
@jwt_required()
def get_installation(inst_id):
    i = NetworkInstallation.query.get_or_404(inst_id)
    return jsonify(i.to_dict())


@bp.post("")
@roles_required("district_admin", "technician")
def create_installation():
    data = request.get_json(force=True) or {}
    if not data.get("branch_id"):
        return jsonify({"error": "'branch_id' is required"}), 400
    branch = Branch.query.get(data["branch_id"])
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    inst = NetworkInstallation(
        branch_id=data["branch_id"],
        installation_type=data.get("installation_type"),
        technician_id=data.get("technician_id"),
        start_date=data.get("start_date") or None,
        expected_completion=data.get("expected_completion") or None,
        status=data.get("status", "PLANNED"),
        notes=data.get("notes"),
        checklist={item: False for item in CHECKLIST_ITEMS},
    )
    db.session.add(inst)
    db.session.commit()

    for eq in data.get("equipment", []):
        equipment = NetworkEquipment(
            installation_id=inst.id,
            equipment_type=eq.get("equipment_type"),
            model=eq.get("model"),
            serial_number=eq.get("serial_number"),
            quantity=eq.get("quantity", 1),
            status=eq.get("status", "INSTALLED"),
        )
        db.session.add(equipment)
    db.session.commit()

    audit("Network installation created", f"New installation project at {branch.name}")
    return jsonify(inst.to_dict()), 201


@bp.put("/<int:inst_id>")
@roles_required("district_admin", "technician")
def update_installation(inst_id):
    inst = NetworkInstallation.query.get_or_404(inst_id)
    data = request.get_json(force=True) or {}
    for field in [
        "installation_type", "technician_id", "start_date", "expected_completion",
        "actual_completion", "status", "problems", "notes",
    ]:
        if field in data:
            setattr(inst, field, data[field])

    if data.get("status") == "COMPLETED" and not inst.actual_completion:
        inst.actual_completion = datetime.utcnow().date()
    if data.get("status") == "FAILED":
        notify(
            title=f"Network installation failed - {inst.branch.name}",
            message=f"Installation project at {inst.branch.name} was marked FAILED.",
            severity="CRITICAL",
            type="NETWORK_INSTALL_FAILED",
            related_entity="network_installation",
            related_id=inst.id,
        )

    db.session.commit()
    audit("Network installation updated", f"Installation {inst.id} -> {inst.status}")
    return jsonify(inst.to_dict())


@bp.put("/<int:inst_id>/checklist")
@roles_required("district_admin", "technician")
def update_checklist(inst_id):
    inst = NetworkInstallation.query.get_or_404(inst_id)
    data = request.get_json(force=True) or {}
    checklist = dict(inst.checklist or {})
    for key, value in data.items():
        if key in CHECKLIST_ITEMS:
            checklist[key] = bool(value)
    inst.checklist = checklist
    db.session.commit()
    audit("Installation checklist updated", f"Checklist updated for installation {inst.id}")
    return jsonify(inst.to_dict())


@bp.post("/<int:inst_id>/equipment")
@roles_required("district_admin", "technician")
def add_equipment(inst_id):
    inst = NetworkInstallation.query.get_or_404(inst_id)
    data = request.get_json(force=True) or {}
    eq = NetworkEquipment(
        installation_id=inst.id,
        equipment_type=data.get("equipment_type"),
        model=data.get("model"),
        serial_number=data.get("serial_number"),
        quantity=data.get("quantity", 1),
        status=data.get("status", "INSTALLED"),
    )
    db.session.add(eq)
    db.session.commit()
    audit("Network equipment added", f"{eq.equipment_type} added to installation {inst.id}")
    return jsonify(eq.to_dict()), 201


@bp.delete("/<int:inst_id>")
@roles_required("district_admin")
def delete_installation(inst_id):
    inst = NetworkInstallation.query.get_or_404(inst_id)
    db.session.delete(inst)
    db.session.commit()
    audit("Network installation deleted", f"Deleted installation {inst_id}")
    return jsonify({"message": "Installation deleted"})
