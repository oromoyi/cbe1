import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@bp.post("")
@jwt_required()
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not _allowed(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    file.save(path)
    return jsonify({"path": f"/api/uploads/{unique_name}", "filename": safe_name}), 201


@bp.get("/<path:filename>")
@jwt_required()
def get_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
