from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from models import db, ITTicket, TicketComment, Branch, Employee, Computer, Technician
from utils import roles_required, audit, notify, next_code, current_user

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

PROBLEM_CATEGORIES = [
    "Computer not starting", "Windows problem", "Software problem", "Network problem",
    "Internet problem", "Printer problem", "Scanner problem", "Email problem",
    "Login problem", "Slow computer", "Hardware problem", "Virus/security alert", "Other",
]


@bp.get("/categories")
@jwt_required()
def categories():
    return jsonify(PROBLEM_CATEGORIES)


@bp.get("")
@jwt_required()
def list_tickets():
    q = ITTicket.query
    claims = get_jwt()
    role = claims.get("role")
    if role == "branch_employee" or role == "branch_manager":
        branch_id = claims.get("branch_id")
        if branch_id:
            q = q.filter_by(branch_id=branch_id)

    branch_id_param = request.args.get("branch_id")
    status = request.args.get("status")
    priority = request.args.get("priority")
    technician_id = request.args.get("technician_id")
    search = request.args.get("search")
    if branch_id_param:
        q = q.filter_by(branch_id=branch_id_param)
    if status:
        q = q.filter_by(status=status)
    if priority:
        q = q.filter_by(priority=priority)
    if technician_id:
        q = q.filter_by(assigned_technician_id=technician_id)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(ITTicket.ticket_code.ilike(like), ITTicket.description.ilike(like)))
    tickets = q.order_by(ITTicket.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tickets])


@bp.get("/<int:ticket_id>")
@jwt_required()
def get_ticket(ticket_id):
    return jsonify(ITTicket.query.get_or_404(ticket_id).to_dict())


@bp.post("")
@jwt_required()
def create_ticket():
    """Any authenticated role can report a problem (typically branch employees)."""
    data = request.get_json(force=True) or {}
    if not data.get("branch_id") or not data.get("problem_category"):
        return jsonify({"error": "'branch_id' and 'problem_category' are required"}), 400
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    t = ITTicket(
        ticket_code=next_code("IT", ITTicket, "ticket_code", pad=4, start=1000),
        branch_id=data["branch_id"],
        employee_id=data.get("employee_id"),
        computer_id=data.get("computer_id"),
        problem_category=data["problem_category"],
        description=data.get("description"),
        attachment_path=data.get("attachment_path"),
        priority=data.get("priority", "MEDIUM"),
        status="OPEN",
    )
    db.session.add(t)
    db.session.commit()

    notify(
        title=f"New IT ticket {t.ticket_code}",
        message=f"{t.problem_category} reported at branch (priority {t.priority}).",
        severity="CRITICAL" if t.priority == "CRITICAL" else "INFO",
        type="TICKET_NEW",
        related_entity="ticket",
        related_id=t.id,
    )
    audit("Ticket created", f"{t.ticket_code}: {t.problem_category}")
    return jsonify(t.to_dict()), 201


@bp.put("/<int:ticket_id>")
@roles_required("district_admin", "technician")
def update_ticket(ticket_id):
    t = ITTicket.query.get_or_404(ticket_id)
    data = request.get_json(force=True) or {}

    if "assigned_technician_id" in data and data["assigned_technician_id"] and t.status == "OPEN":
        t.status = "ASSIGNED"
        tech = Technician.query.get(data["assigned_technician_id"])
        if tech:
            notify(
                title=f"Ticket {t.ticket_code} assigned to you",
                message=f"You have been assigned ticket {t.ticket_code}.",
                type="TICKET_ASSIGNED",
                user_id=tech.user_id,
                related_entity="ticket",
                related_id=t.id,
            )

    for field in ["assigned_technician_id", "priority", "status", "resolution", "problem_category", "description"]:
        if field in data:
            setattr(t, field, data[field])

    if data.get("status") in ("RESOLVED", "CLOSED") and not t.closed_at:
        t.closed_at = datetime.utcnow()
        notify(
            title=f"Ticket {t.ticket_code} resolved",
            message=f"Ticket {t.ticket_code} has been marked {t.status}.",
            type="TICKET_RESOLVED",
            related_entity="ticket",
            related_id=t.id,
        )

    db.session.commit()
    audit("Ticket updated", f"{t.ticket_code} -> {t.status}")
    return jsonify(t.to_dict())


@bp.post("/<int:ticket_id>/comments")
@jwt_required()
def add_comment(ticket_id):
    t = ITTicket.query.get_or_404(ticket_id)
    data = request.get_json(force=True) or {}
    user = current_user()
    if not data.get("message"):
        return jsonify({"error": "'message' is required"}), 400
    c = TicketComment(
        ticket_id=t.id,
        author_name=user.full_name if user else "Unknown",
        author_role=user.role if user else "unknown",
        message=data["message"],
    )
    db.session.add(c)
    db.session.commit()
    audit("Ticket comment added", f"Comment added to {t.ticket_code}")
    return jsonify(c.to_dict()), 201
