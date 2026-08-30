from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from datetime import datetime, timedelta, date

from models import (
    db, Branch, ATM, ATMError, NetworkInstallation, Computer, ITTicket,
    Technician, Incident, DailyMetricSnapshot, DASHBOARD_METRIC_FIELDS,
)

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def compute_summary_metrics():
    """Compute the current live values for every dashboard KPI. Shared by
    the /summary endpoint and the daily snapshot capture (and by seed.py
    when backfilling demo history) so there is a single source of truth."""
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

    return {
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
    }


def capture_today_snapshot(metrics):
    """Upsert today's DailyMetricSnapshot row with the given metrics dict.
    Safe to call repeatedly during the day — it just keeps 'today' current."""
    today = date.today()
    row = DailyMetricSnapshot.query.filter_by(snapshot_date=today).first()
    if not row:
        row = DailyMetricSnapshot(snapshot_date=today)
        db.session.add(row)
    for field in DASHBOARD_METRIC_FIELDS:
        setattr(row, field, metrics.get(field, 0))
    db.session.commit()


@bp.get("/summary")
@jwt_required()
def summary():
    metrics = compute_summary_metrics()
    try:
        capture_today_snapshot(metrics)
    except Exception:
        db.session.rollback()  # never let snapshot bookkeeping break the dashboard
    return jsonify(metrics)


@bp.get("/trends")
@jwt_required()
def trends():
    """Real (not fabricated) trend data for the KPI sparklines/arrows,
    built from the daily snapshot history. Days without a snapshot yet
    (e.g. a freshly-deployed instance) simply aren't included — the
    frontend shows a flat '—' for metrics with fewer than 2 data points."""
    days = min(int(request.args.get("days", 14)), 90)
    since = date.today() - timedelta(days=days - 1)
    rows = (
        DailyMetricSnapshot.query
        .filter(DailyMetricSnapshot.snapshot_date >= since)
        .order_by(DailyMetricSnapshot.snapshot_date.asc())
        .all()
    )

    result = {}
    dates = [r.snapshot_date.isoformat() for r in rows]
    for field in DASHBOARD_METRIC_FIELDS:
        series = [getattr(r, field) for r in rows]
        if len(series) >= 2 and series[0] != 0:
            change_pct = round(((series[-1] - series[0]) / abs(series[0])) * 100, 1)
        elif len(series) >= 2:
            change_pct = 100.0 if series[-1] > 0 else 0.0
        else:
            change_pct = 0.0
        if len(series) < 2 or series[-1] == series[0]:
            direction = "flat"
        elif series[-1] > series[0]:
            direction = "up"
        else:
            direction = "down"
        result[field] = {
            "series": series,
            "change_pct": change_pct,
            "direction": direction,
        }

    return jsonify({"dates": dates, "metrics": result})


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
