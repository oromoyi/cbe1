import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from models import db, User, Technician, Employee, Branch
from utils import roles_required, audit

bp = Blueprint("users", __name__, url_prefix="/api/users")
tech_bp = Blueprint("technicians", __name__, url_prefix="/api/technicians")
emp_bp = Blueprint("employees", __name__, url_prefix="/api/employees")


# --- Users -----------------------------------------------------------
@bp.get("")
@roles_required("district_admin")
def list_users():
    q = User.query
    role = request.args.get("role")
    if role:
        q = q.filter_by(role=role)
    return jsonify([u.to_dict() for u in q.order_by(User.full_name).all()])


@bp.post("")
@roles_required("district_admin")
def create_user():
    data = request.get_json(force=True) or {}
    required = ["full_name", "username", "email", "password", "role"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"'{f}' is required"}), 400
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409
    if data["role"] not in ("district_admin", "technician", "branch_employee", "branch_manager"):
        return jsonify({"error": "Invalid role"}), 400

    u = User(
        full_name=data["full_name"],
        username=data["username"],
        email=data["email"],
        role=data["role"],
        branch_id=data.get("branch_id"),
    )
    u.set_password(data["password"])
    db.session.add(u)
    db.session.commit()

    if data["role"] == "technician":
        t = Technician(
            user_id=u.id,
            full_name=u.full_name,
            specialty=data.get("specialty", "General"),
            branch_id=data.get("branch_id"),
            phone=data.get("phone"),
        )
        db.session.add(t)
        db.session.commit()

    audit("User created", f"Created user {u.username} ({u.role})")
    return jsonify(u.to_dict()), 201


@bp.put("/<int:user_id>")
@roles_required("district_admin")
def update_user(user_id):
    u = User.query.get_or_404(user_id)
    data = request.get_json(force=True) or {}
    if "email" in data and User.query.filter(User.email == data["email"], User.id != u.id).first():
        return jsonify({"error": "Email already exists"}), 409
    if data.get("role") and data["role"] not in ("district_admin", "technician", "branch_employee", "branch_manager"):
        return jsonify({"error": "Invalid role"}), 400
    for field in ["full_name", "email", "role", "branch_id", "is_active"]:
        if field in data:
            setattr(u, field, data[field])
    if data.get("password"):
        u.set_password(data["password"])
    db.session.commit()
    audit("User updated", f"Updated user {u.username}")
    return jsonify(u.to_dict())


@bp.post("/<int:user_id>/reset-password")
@roles_required("district_admin")
def reset_password(user_id):
    u = User.query.get_or_404(user_id)
    password = (request.get_json(force=True) or {}).get("password", "")
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    u.set_password(password)
    db.session.commit()
    audit("Password reset", f"Reset password for {u.username}")
    return jsonify({"message": "Password reset successfully"})


@bp.post("/<int:user_id>/photo")
@roles_required("district_admin")
def upload_profile_photo(user_id):
    u = User.query.get_or_404(user_id)
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No photo selected"}), 400
    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in {"png", "jpg", "jpeg", "gif", "webp"}:
        return jsonify({"error": "Only PNG, JPG, GIF, and WEBP photos are allowed"}), 400
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = f"profile_{u.id}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    u.profile_photo = f"/api/uploads/{filename}"
    db.session.commit()
    return jsonify(u.to_dict())


@bp.delete("/<int:user_id>")
@roles_required("district_admin")
def delete_user(user_id):
    u = User.query.get_or_404(user_id)
    username = u.username
    db.session.delete(u)
    db.session.commit()
    audit("User deleted", f"Deleted user {username}")
    return jsonify({"message": "User deleted"})


# --- Technicians -------------------------------------------------------
@tech_bp.get("")
@jwt_required()
def list_technicians():
    q = Technician.query
    branch_id = request.args.get("branch_id")
    specialty = request.args.get("specialty")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if specialty:
        q = q.filter_by(specialty=specialty)
    return jsonify([t.to_dict() for t in q.order_by(Technician.full_name).all()])


@tech_bp.put("/<int:tech_id>")
@roles_required("district_admin")
def update_technician(tech_id):
    t = Technician.query.get_or_404(tech_id)
    data = request.get_json(force=True) or {}
    for field in ["specialty", "branch_id", "phone", "is_active"]:
        if field in data:
            setattr(t, field, data[field])
    db.session.commit()
    audit("Technician updated", f"Updated technician {t.full_name}")
    return jsonify(t.to_dict())


# --- Employees -----------------------------------------------------
@emp_bp.get("")
@jwt_required()
def list_employees():
    q = Employee.query
    branch_id = request.args.get("branch_id")
    search = request.args.get("search")
    if branch_id:
        q = q.filter_by(branch_id=branch_id)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Employee.full_name.ilike(like), Employee.employee_id_code.ilike(like)))
    return jsonify([e.to_dict() for e in q.order_by(Employee.full_name).all()])


@emp_bp.post("")
@roles_required("district_admin", "technician")
def create_employee():
    data = request.get_json(force=True) or {}
    if not data.get("employee_id_code") or not data.get("full_name") or not data.get("branch_id"):
        return jsonify({"error": "'employee_id_code', 'full_name', and 'branch_id' are required"}), 400
    if Employee.query.filter_by(employee_id_code=data["employee_id_code"]).first():
        return jsonify({"error": "Employee ID already exists"}), 409
    if not Branch.query.get(data["branch_id"]):
        return jsonify({"error": "Branch not found"}), 404

    e = Employee(
        employee_id_code=data["employee_id_code"],
        full_name=data["full_name"],
        branch_id=data["branch_id"],
        department=data.get("department"),
        phone=data.get("phone"),
    )
    db.session.add(e)
    db.session.commit()
    audit("Employee registered", f"Registered employee {e.full_name}")
    return jsonify(e.to_dict()), 201
