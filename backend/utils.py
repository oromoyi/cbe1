from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

from models import db, User, Notification, AuditLog


def roles_required(*roles):
    """Decorator restricting an endpoint to specific roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"error": "Forbidden: insufficient role"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    verify_jwt_in_request()
    uid = get_jwt_identity()
    return User.query.get(int(uid))


def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def audit(action, description=""):
    try:
        user = current_user()
    except Exception:
        user = None
    entry = AuditLog(
        user_id=user.id if user else None,
        user_name=user.full_name if user else "System",
        action=action,
        description=description,
        ip_address=client_ip(),
    )
    db.session.add(entry)
    db.session.commit()


def notify(title, message, severity="INFO", type="GENERAL", user_id=None,
           related_entity=None, related_id=None):
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        severity=severity,
        related_entity=related_entity,
        related_id=related_id,
    )
    db.session.add(n)
    db.session.commit()
    return n


def next_code(prefix, model, field, pad=4, start=1000):
    """Generate the next sequential business code, e.g. IT-1024, ATM-001, INC-2001."""
    last = model.query.order_by(model.id.desc()).first()
    if not last:
        num = start
    else:
        try:
            num = int(getattr(last, field).split("-")[-1]) + 1
        except Exception:
            num = model.query.count() + start + 1
    return f"{prefix}-{str(num).zfill(pad)}"


def paginate_query(query, default_limit=50):
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", default_limit))
    except ValueError:
        page, limit = 1, default_limit
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return items, {"page": page, "limit": limit, "total": total}
