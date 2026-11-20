from extensions import db
from models.user import User
from models.plant import PlantArea
from models.equipment import Equipment
from models.sensor import SensorDefinition, SensorReading
from models.simulation import SimulationRun
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from models.audit import AuditLog
from models.notification import NotificationLog

__all__ = [
    "db",
    "User",
    "PlantArea",
    "Equipment",
    "SensorDefinition",
    "SensorReading",
    "SimulationRun",
    "FaultAlert",
    "FailurePrediction",
    "WorkOrder",
    "MaintenanceRecord",
    "MaintenanceSchedule",
    "AuditLog",
    "NotificationLog",
]
