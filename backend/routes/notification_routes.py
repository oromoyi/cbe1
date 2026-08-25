from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db, Notification
from utils import audit

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
@jwt_required()
def list_notifications():
    uid = int(get_jwt_identity())
    q = Notification.query.filter(db.or_(Notification.user_id == uid, Notification.user_id.is_(None)))
    unread_only = request.args.get("unread_only")
    if unread_only == "true":
        q = q.filter_by(is_read=False)
    items = q.order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify([n.to_dict() for n in items])


@bp.get("/unread-count")
@jwt_required()
def unread_count():
    uid = int(get_jwt_identity())
    count = Notification.query.filter(
        db.or_(Notification.user_id == uid, Notification.user_id.is_(None)),
        Notification.is_read == False,  # noqa: E712
    ).count()
    return jsonify({"unread_count": count})


@bp.put("/<int:n_id>/read")
@jwt_required()
def mark_read(n_id):
    n = Notification.query.get_or_404(n_id)
    n.is_read = True
    db.session.commit()
    return jsonify(n.to_dict())


@bp.put("/mark-all-read")
@jwt_required()
def mark_all_read():
    uid = int(get_jwt_identity())
    Notification.query.filter(
        db.or_(Notification.user_id == uid, Notification.user_id.is_(None))
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"})
