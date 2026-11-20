"""
Sugar Plant Predictive Maintenance System
Full-stack industrial simulation and maintenance management web platform.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, g, session
from dotenv import load_dotenv

from extensions import db
from models.user import User
from services.auth_service import get_current_user
from services.simulator import simulator

# Load environment variables
load_dotenv()


def create_app(config_name=None):
    """Application factory."""
    app = Flask(__name__)

    # ── Core configuration ──────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-sugar-plant-secret-key-2026")
    is_vercel = bool(os.environ.get("VERCEL"))

    try:
        import db_config
        cloud_uri = getattr(db_config, "CLOUD_DATABASE_URI", "").strip()
    except Exception:
        cloud_uri = ""

    db_uri = cloud_uri or os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")

    # Normalize PostgreSQL URI to use psycopg2 driver and handle special characters in password
    if db_uri:
        if db_uri.startswith("postgres://"):
            db_uri = db_uri.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_uri.startswith("postgresql://") and not db_uri.startswith("postgresql+"):
            db_uri = db_uri.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Handle unescaped '@' characters in database password
        try:
            import urllib.parse
            if "://" in db_uri and db_uri.count("@") > 1:
                scheme, rest = db_uri.split("://", 1)
                last_at_idx = rest.rfind("@")
                user_pass = rest[:last_at_idx]
                host_db = rest[last_at_idx + 1:]
                if ":" in user_pass:
                    user, password = user_pass.split(":", 1)
                    encoded_pw = urllib.parse.quote_plus(password)
                    db_uri = f"{scheme}://{user}:{encoded_pw}@{host_db}"
        except Exception:
            pass

    if not db_uri or (is_vercel and "127.0.0.1" in db_uri):
        if is_vercel:
            # Serverless fallback if custom cloud database is not yet configured
            db_uri = "sqlite:////tmp/sugar_plant.db"
        else:
            db_uri = "mysql+pymysql://root:@127.0.0.1:3306/sugar_plant_maintenance"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

    if "sqlite" in db_uri:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False},
        }
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

    if config_name == "testing":
        from sqlalchemy.pool import StaticPool
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }

    # ── Initialize extensions ───────────────────────────────────────────────
    db.init_app(app)
    simulator.init_app(app)

    # ── Context Processors ──────────────────────────────────────────────────
    @app.context_processor
    def inject_global_template_vars():
        return {
            "current_user": get_current_user(),
            "User": User,
            "now": datetime.now(timezone.utc),
            "simulator": simulator,
        }

    # ── Register Blueprints ─────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.plant_areas import plant_areas_bp
    from routes.equipment import equipment_bp
    from routes.simulation import simulation_bp
    from routes.sensors import sensors_bp
    from routes.alerts import alerts_bp
    from routes.predictions import predictions_bp
    from routes.maintenance import maintenance_bp
    from routes.reports import reports_bp
    from routes.users import users_bp
    from routes.settings import settings_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(plant_areas_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(sensors_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(notifications_bp)

    # ── Health-check routes ─────────────────────────────────────────────────
    @app.route("/health")
    def health():
        """Basic liveness probe."""
        return (
            json.dumps({"status": "ok", "service": "sugar_plant_maintenance"}),
            200,
            {"Content-Type": "application/json"},
        )

    @app.route("/health/db")
    def health_db():
        """Database readiness probe."""
        try:
            db.session.execute(db.text("SELECT 1"))
            return (
                json.dumps({"status": "ok", "database": "connected"}),
                200,
                {"Content-Type": "application/json"},
            )
        except Exception:
            return (
                json.dumps({"status": "error", "database": "unreachable"}),
                503,
                {"Content-Type": "application/json"},
            )

    # ── Error Handlers ──────────────────────────────────────────────────────
    @app.errorhandler(500)
    def handle_500(e):
        return render_template("auth/login.html", error=f"Server Error: {e}"), 500

    # ── Auto-initialize tables & default admin ──────────────────────────────
    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                db.create_all()
                if not User.query.filter_by(username="admin").first():
                    from database.seed_data import seed_database
                    seed_database(app)
            except Exception as e:
                app.logger.warning(f"Database auto-init notice: {e}")

    return app


# ── Entry point ─────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", host="0.0.0.0", port=5000)
