import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Central configuration for the CBE District IT Management and
    Remote Support System.

    All secrets are read from environment variables. Sensible development
    defaults are provided ONLY for local/educational use — replace them
    with real secrets (via environment variables) before any real deployment.
    """

    # --- Core / Secrets -----------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_TOKEN_LOCATION = ["headers"]

    # --- Database --------------------------------------------------------
    default_database_url = (
        "sqlite:////tmp/cbe_it.db"
        if os.environ.get("VERCEL")
        else f"sqlite:///{os.path.join(BASE_DIR, 'cbe_it.db')}"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", default_database_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads -----------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "log", "csv"}

    # --- Simulation mode -----------------------------------------------
    # IMPORTANT (see project requirement #27):
    # This system does NOT connect to any real ATM network, banking core
    # system, or production infrastructure. ATM/network "checks" performed
    # here are SIMULATED for demonstration/educational purposes unless an
    # authorized monitoring integration is explicitly configured below.
    SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "true").lower() == "true"
    AUTHORIZED_MONITORING_API_URL = os.environ.get("AUTHORIZED_MONITORING_API_URL", "")

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
