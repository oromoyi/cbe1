from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from models import db, User
from utils import audit, current_user

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401
    if not user.is_active:
        return jsonify({"error": "This account has been disabled. Contact your administrator."}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "branch_id": user.branch_id, "username": user.username},
    )
    audit("User logged in", f"{user.username} ({user.role}) logged in")
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())


@bp.post("/change-password")
@jwt_required()
def change_password():
    user = current_user()
    data = request.get_json(force=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    if not user.check_password(old_password):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
    user.set_password(new_password)
    db.session.commit()
    audit("Password changed", f"{user.username} changed their password")
    return jsonify({"message": "Password updated successfully"})
