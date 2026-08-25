from flask import Blueprint, request, jsonify

from models import AuditLog
from utils import roles_required, paginate_query

bp = Blueprint("audit", __name__, url_prefix="/api/audit-logs")


@bp.get("")
@roles_required("district_admin")
def list_audit_logs():
    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    user_name = request.args.get("user")
    action = request.args.get("action")
    if user_name:
        q = q.filter(AuditLog.user_name.ilike(f"%{user_name}%"))
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    items, meta = paginate_query(q, default_limit=100)
    return jsonify({"items": [i.to_dict() for i in items], "meta": meta})
