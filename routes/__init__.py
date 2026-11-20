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

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "plant_areas_bp",
    "equipment_bp",
    "simulation_bp",
    "sensors_bp",
    "alerts_bp",
    "predictions_bp",
    "maintenance_bp",
    "reports_bp",
    "users_bp",
    "settings_bp",
]
