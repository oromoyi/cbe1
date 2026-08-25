from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from datetime import datetime, timedelta

from models import (
    db, Branch, ATM, ATMError, NetworkInstallation, Computer, ITTicket,
    Technician, Incident,
)

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/summary")
@jwt_required()
def summary():
    total_branches = Branch.query.count()
    total_atms = ATM.query.count()
    operational_atms = ATM.query.filter_by(status="ONLINE").count()
    offline_atms = ATM.query.filter(ATM.status.in_(["OFFLINE", "ERROR"])).count()
    atm_errors = ATMError.query.filter(ATMError.status != "RESOLVED").count()

    pending_tickets = ITTicket.query.filter_by(status="OPEN").count()
    in_progress_tickets = ITTicket.query.filter(
        ITTicket.status.in_(["ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER"])
    ).count()
    resolved_tickets = ITTicket.query.filter(ITTicket.status.in_(["RESOLVED", "CLOSED"])).count()

    network_installations = NetworkInstallation.query.count()
    completed_installations = NetworkInstallation.query.filter_by(status="COMPLETED").count()
    pending_installations = NetworkInstallation.query.filter(
        NetworkInstallation.status.in_(["PLANNED", "IN_PROGRESS", "TESTING"])
    ).count()

    computers_with_problems = Computer.query.filter(
        Computer.status.in_(["ERROR", "WARNING", "OFFLINE"])
    ).count()
    active_technicians = Technician.query.filter_by(is_active=True).count()

    return jsonify({
        "total_branches": total_branches,
        "total_atms": total_atms,
        "operational_atms": operational_atms,
        "offline_atms": offline_atms,
        "atm_errors": atm_errors,
        "pending_tickets": pending_tickets,
        "in_progress_tickets": in_progress_tickets,
        "resolved_tickets": resolved_tickets,
        "network_installations": network_installations,
        "completed_installations": completed_installations,
        "pending_installations": pending_installations,
        "computers_with_problems": computers_with_problems,
        "active_technicians": active_technicians,
    })


@bp.get("/charts")
@jwt_required()
def charts():
    # ATM status distribution
    atm_status = dict(
        db.session.query(ATM.status, func.count(ATM.id)).group_by(ATM.status).all()
    )

    # Incidents by branch
    incidents_by_branch = (
        db.session.query(Branch.name, func.count(Incident.id))
        .join(Incident, Incident.branch_id == Branch.id)
        .group_by(Branch.name)
        .all()
    )

    # Error types (atm errors)
    error_types = dict(
        db.session.query(ATMError.error_group, func.count(ATMError.id))
        .group_by(ATMError.error_group)
        .all()
    )

    # Monthly support requests (last 6 months) based on ticket created_at
    months = []
    counts = []
    today = datetime.utcnow().replace(day=1)
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=1)) if i == 0 else today
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        month_label = datetime(y, m, 1).strftime("%b %Y")
        count = ITTicket.query.filter(
            func.strftime("%Y-%m", ITTicket.created_at) == f"{y}-{str(m).zfill(2)}"
        ).count()
        months.append(month_label)
        counts.append(count)

    # Network installation progress
    installation_progress = dict(
        db.session.query(NetworkInstallation.status, func.count(NetworkInstallation.id))
        .group_by(NetworkInstallation.status)
        .all()
    )

    # Resolved vs unresolved (tickets)
    resolved = ITTicket.query.filter(ITTicket.status.in_(["RESOLVED", "CLOSED"])).count()
    unresolved = ITTicket.query.filter(ITTicket.status.notin_(["RESOLVED", "CLOSED"])).count()

    return jsonify({
        "atm_status": atm_status,
        "incidents_by_branch": {name: c for name, c in incidents_by_branch},
        "error_types": {k or "Unclassified": v for k, v in error_types.items()},
        "monthly_support_requests": {"labels": months, "values": counts},
        "installation_progress": installation_progress,
        "resolved_vs_unresolved": {"resolved": resolved, "unresolved": unresolved},
    })
