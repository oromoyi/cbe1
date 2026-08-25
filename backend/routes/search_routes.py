from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from models import db, Branch, ATM, Computer, Employee, ITTicket, Incident, Asset, Technician

bp = Blueprint("search", __name__, url_prefix="/api/search")


@bp.get("")
@jwt_required()
def global_search():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"branches": [], "atms": [], "computers": [], "employees": [],
                         "tickets": [], "incidents": [], "assets": [], "technicians": []})
    like = f"%{query}%"

    branches = Branch.query.filter(
        db.or_(Branch.name.ilike(like), Branch.branch_code.ilike(like))
    ).limit(10).all()
    atms = ATM.query.filter(
        db.or_(ATM.atm_code.ilike(like), ATM.serial_number.ilike(like))
    ).limit(10).all()
    computers = Computer.query.filter(
        db.or_(Computer.asset_number.ilike(like), Computer.hostname.ilike(like))
    ).limit(10).all()
    employees = Employee.query.filter(
        db.or_(Employee.full_name.ilike(like), Employee.employee_id_code.ilike(like))
    ).limit(10).all()
    tickets = ITTicket.query.filter(ITTicket.ticket_code.ilike(like)).limit(10).all()
    incidents = Incident.query.filter(Incident.incident_code.ilike(like)).limit(10).all()
    assets = Asset.query.filter(
        db.or_(Asset.asset_code.ilike(like), Asset.serial_number.ilike(like))
    ).limit(10).all()
    technicians = Technician.query.filter(Technician.full_name.ilike(like)).limit(10).all()

    return jsonify({
        "branches": [b.to_dict() for b in branches],
        "atms": [a.to_dict() for a in atms],
        "computers": [c.to_dict() for c in computers],
        "employees": [e.to_dict() for e in employees],
        "tickets": [t.to_dict() for t in tickets],
        "incidents": [i.to_dict() for i in incidents],
        "assets": [a.to_dict() for a in assets],
        "technicians": [t.to_dict() for t in technicians],
    })
