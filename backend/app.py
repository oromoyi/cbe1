import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from models import db, User, Branch


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # --- Register blueprints ---
    from routes.auth_routes import bp as auth_bp
    from routes.dashboard_routes import bp as dashboard_bp
    from routes.branch_routes import bp as branch_bp
    from routes.atm_routes import bp as atm_bp
    from routes.network_routes import bp as network_bp
    from routes.computer_routes import bp as computer_bp
    from routes.ticket_routes import bp as ticket_bp
    from routes.incident_routes import bp as incident_bp
    from routes.asset_routes import bp as asset_bp
    from routes.maintenance_routes import bp as maintenance_bp
    from routes.remote_support_routes import bp as remote_support_bp
    from routes.knowledge_routes import bp as knowledge_bp
    from routes.user_routes import bp as users_bp, tech_bp, emp_bp
    from routes.notification_routes import bp as notification_bp
    from routes.audit_routes import bp as audit_bp
    from routes.search_routes import bp as search_bp
    from routes.report_routes import bp as report_bp
    from routes.upload_routes import bp as upload_bp
    from routes.settings_routes import bp as settings_bp

    for bp in [
        auth_bp, dashboard_bp, branch_bp, atm_bp, network_bp, computer_bp,
        ticket_bp, incident_bp, asset_bp, maintenance_bp, remote_support_bp,
        knowledge_bp, users_bp, tech_bp, emp_bp, notification_bp, audit_bp,
        search_bp, report_bp, upload_bp, settings_bp,
    ]:
        app.register_blueprint(bp)

    if os.environ.get("VERCEL"):
        with app.app_context():
            db.create_all()
            if not Branch.query.first():
                from seed import main as seed_database
                seed_database(app)

    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "system": "CBE District IT Management and Remote Support System",
            "simulation_mode": app.config["SIMULATION_MODE"],
        })

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    # --- Serve frontend (single-page app) ---
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/<path:path>")
    def static_proxy(path):
        full_path = os.path.join(frontend_dir, path)
        if os.path.exists(full_path):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
