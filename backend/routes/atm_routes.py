import random
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

from models import db, ATM, ATMCheck, ATMError, Branch, Technician
from utils import roles_required, audit, notify, next_code, current_user

bp = Blueprint("atms", __name__, url_prefix="/api/atms")

ERROR_CATALOG = {
    "Network": [
        "Network disconnected", "IP address problem", "Gateway problem",
        "DNS problem", "Network timeout", "Connection refused",
    ],
    "Hardware": [
        "Card reader error", "Cash dispenser error", "Receipt printer error",
        "Display error", "Keyboard error", "Sensor error", "Power failure",
    ],
    "Software": [
        "Application failure", "Operating system error", "Service stopped",
        "Configuration error", "Software crash",
    ],
    "Security": [
        "Authentication failure", "Communication security error", "Access denied",
    ],
    "Other": [
        "Unknown error", "Maintenance required", "Device unavailable",
    ],
}


@bp.get("/error-catalog")
@jwt_required()
def error_catalog():
    return jsonify(ERROR_CATALOG)


@bp.get("")
@jwt_required()
def list_atms():
    q = ATM.query
    branch_id = request.args.get("branch_id")
    status = request.args.get("status")
    search = request.args.get("search")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if status:
        q = q.filter_by(status=status)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(ATM.atm_code.ilike(like), ATM.serial_number.ilike(like)))
    atms = q.order_by(ATM.atm_code).all()
    return jsonify([a.to_dict() for a in atms])


@bp.get("/<int:atm_id>")
@jwt_required()
def get_atm(atm_id):
    a = ATM.query.get_or_404(atm_id)
    data = a.to_dict()
    data["checks"] = [c.to_dict() for c in ATMCheck.query.filter_by(atm_id=atm_id).order_by(ATMCheck.check_time.desc()).limit(20)]
    data["errors"] = [e.to_dict() for e in ATMError.query.filter_by(atm_id=atm_id).order_by(ATMError.created_at.desc())]
    return jsonify(data)


@bp.post("")
@roles_required("district_admin", "technician")
def create_atm():
    data = request.get_json(force=True) or {}
    if not data.get("atm_code") or not data.get("branch_id"):
        return jsonify({"error": "'atm_code' and 'branch_id' are required"}), 400
    if ATM.query.filter_by(atm_code=data["atm_code"]).first():
        return jsonify({"error": "ATM code already exists"}), 409
    branch = Branch.query.get(data["branch_id"])
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    a = ATM(
        atm_code=data["atm_code"],
        serial_number=data.get("serial_number"),
        branch_id=data["branch_id"],
        location_description=data.get("location_description"),
        ip_address=data.get("ip_address"),
        network_connection=data.get("network_connection", "CONNECTED"),
        model_type=data.get("model_type"),
        installation_date=data.get("installation_date") or None,
        status=data.get("status", "UNKNOWN"),
        technician_id=data.get("technician_id"),
    )
    db.session.add(a)
    db.session.commit()
    audit("ATM registered", f"Registered {a.atm_code} at {branch.name}")
    return jsonify(a.to_dict()), 201


@bp.put("/<int:atm_id>")
@roles_required("district_admin", "technician")
def update_atm(atm_id):
    a = ATM.query.get_or_404(atm_id)
    data = request.get_json(force=True) or {}
    for field in [
        "serial_number", "location_description", "ip_address", "network_connection",
        "model_type", "installation_date", "last_maintenance_date", "status",
        "error_status", "technician_id",
    ]:
        if field in data:
            setattr(a, field, data[field])
    db.session.commit()
    audit("ATM updated", f"Updated ATM {a.atm_code} (status: {a.status})")
    return jsonify(a.to_dict())


@bp.delete("/<int:atm_id>")
@roles_required("district_admin")
def delete_atm(atm_id):
    a = ATM.query.get_or_404(atm_id)
    code = a.atm_code
    db.session.delete(a)
    db.session.commit()
    audit("ATM deleted", f"Deleted ATM {code}")
    return jsonify({"message": "ATM deleted"})


@bp.post("/<int:atm_id>/check")
@roles_required("district_admin", "technician")
def check_atm(atm_id):
    """
    Perform an ATM status check.

    IMPORTANT (see project requirement #27 / #7):
    Unless AUTHORIZED_MONITORING_API_URL is configured (a real, approved
    monitoring integration), this endpoint performs a SIMULATED check for
    demonstration purposes. It never claims a real ATM is online just
    because this web server is running.
    """
    a = ATM.query.get_or_404(atm_id)
    data = request.get_json(silent=True) or {}
    user = current_user()
    technician = Technician.query.filter_by(user_id=user.id).first() if user else None

    is_simulated = not bool(current_app.config.get("AUTHORIZED_MONITORING_API_URL"))

    if is_simulated:
        # Clearly-labeled simulation: technician may confirm manually,
        # or the system generates a plausible simulated reading.
        manual_status = data.get("availability_status")
        if manual_status:
            availability = manual_status
            network = data.get("network_status", "CONNECTED" if availability == "ONLINE" else "DISCONNECTED")
            error = data.get("error")
        else:
            availability = random.choices(
                ["ONLINE", "OFFLINE", "WARNING", "ERROR"], weights=[70, 10, 12, 8]
            )[0]
            network = "CONNECTED" if availability in ("ONLINE", "WARNING") else "DISCONNECTED"
            error = None if availability == "ONLINE" else "Simulated check flagged a possible issue"
    else:
        # Placeholder for a real, authorized monitoring API integration.
        # A real implementation would call current_app.config["AUTHORIZED_MONITORING_API_URL"]
        # here using an authenticated request and parse its response.
        availability = data.get("availability_status", "UNKNOWN")
        network = data.get("network_status", "UNKNOWN")
        error = data.get("error")

    check = ATMCheck(
        atm_id=a.id,
        branch_id=a.branch_id,
        network_status=network,
        availability_status=availability,
        error=error,
        technician_id=technician.id if technician else None,
        notes=data.get("notes"),
        is_simulated=is_simulated,
    )
    db.session.add(check)

    a.status = availability
    a.network_connection = network
    a.error_status = error
    a.last_checked_at = datetime.utcnow()
    a.is_simulated = is_simulated
    if technician:
        a.technician_id = technician.id
    db.session.commit()

    if availability in ("OFFLINE", "ERROR"):
        notify(
            title=f"ATM {a.atm_code} is {availability}",
            message=f"{a.atm_code} at {a.branch.name} reported status {availability}.",
            severity="CRITICAL" if availability == "ERROR" else "WARNING",
            type="ATM_OFFLINE" if availability == "OFFLINE" else "ATM_CRITICAL",
            related_entity="atm",
            related_id=a.id,
        )

    audit("ATM checked", f"Checked {a.atm_code} -> {availability} ({'simulated' if is_simulated else 'real monitoring'})")
    return jsonify({"atm": a.to_dict(), "check": check.to_dict()})


# --- ATM Errors -------------------------------------------------------
@bp.get("/errors/list")
@jwt_required()
def list_errors():
    q = ATMError.query
    branch_id = request.args.get("branch_id")
    status = request.args.get("status")
    severity = request.args.get("severity")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if status:
        q = q.filter_by(status=status)
    if severity:
        q = q.filter_by(severity=severity)
    errors = q.order_by(ATMError.created_at.desc()).all()
    return jsonify([e.to_dict() for e in errors])


@bp.post("/errors")
@roles_required("district_admin", "technician")
def create_error():
    data = request.get_json(force=True) or {}
    for f in ["atm_id", "error_type", "error_group"]:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400
    atm = ATM.query.get(data["atm_id"])
    if not atm:
        return jsonify({"error": "ATM not found"}), 404

    user = current_user()
    technician = Technician.query.filter_by(user_id=user.id).first() if user else None

    err = ATMError(
        error_code=data.get("error_code") or next_code("ERR", ATMError, "error_code"),
        error_type=data["error_type"],
        error_group=data["error_group"],
        description=data.get("description"),
        branch_id=atm.branch_id,
        atm_id=atm.id,
        severity=data.get("severity", "MEDIUM"),
        technician_id=technician.id if technician else data.get("technician_id"),
        status="OPEN",
    )
    db.session.add(err)
    atm.status = "ERROR"
    atm.error_status = err.error_type
    db.session.commit()

    notify(
        title=f"New ATM error at {atm.atm_code}",
        message=f"{err.error_type} ({err.severity}) reported for {atm.atm_code}.",
        severity="CRITICAL" if err.severity == "CRITICAL" else "WARNING",
        type="ATM_CRITICAL",
        related_entity="atm_error",
        related_id=err.id,
    )
    audit("ATM error recorded", f"{err.error_type} on {atm.atm_code}")
    return jsonify(err.to_dict()), 201


@bp.put("/errors/<int:error_id>")
@roles_required("district_admin", "technician")
def update_error(error_id):
    err = ATMError.query.get_or_404(error_id)
    data = request.get_json(force=True) or {}
    for field in ["error_type", "error_group", "description", "severity", "resolution", "status", "technician_id"]:
        if field in data:
            setattr(err, field, data[field])
    if data.get("status") == "RESOLVED" and not err.resolved_at:
        err.resolved_at = datetime.utcnow()
        if err.atm and err.atm.status == "ERROR":
            err.atm.status = "ONLINE"
            err.atm.error_status = None
    db.session.commit()
    audit("ATM error updated", f"Error {err.error_code} -> {err.status}")
    return jsonify(err.to_dict())
