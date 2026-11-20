from datetime import datetime, timezone
from extensions import db


class Equipment(db.Model):
    __tablename__ = "equipment"

    STATUS_RUNNING = "running"
    STATUS_IDLE = "idle"
    STATUS_STOPPED = "stopped"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_DECOMMISSIONED = "decommissioned"

    EQUIPMENT_TYPES = [
        "Conveyor Belt",
        "Electric Motor",
        "Bearing",
        "Pump",
        "Boiler",
        "Steam Pipe",
        "Gearbox",
        "Fan",
        "Crusher",
        "Centrifugal Machine",
    ]

    id = db.Column(db.Integer, primary_key=True)
    equipment_tag = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    equipment_type = db.Column(db.String(80), nullable=False)
    plant_area_id = db.Column(db.Integer, db.ForeignKey("plant_areas.id"), nullable=False)
    description = db.Column(db.Text, nullable=True)
    operating_status = db.Column(db.String(30), default=STATUS_RUNNING, nullable=False)
    installation_date = db.Column(db.Date, nullable=True)
    maintenance_info = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    plant_area = db.relationship("PlantArea", back_populates="equipment")
    sensors = db.relationship("SensorDefinition", back_populates="equipment", cascade="all, delete-orphan")
    readings = db.relationship("SensorReading", back_populates="equipment", cascade="all, delete-orphan")
    alerts = db.relationship("FaultAlert", back_populates="equipment", cascade="all, delete-orphan")
    work_orders = db.relationship("WorkOrder", back_populates="equipment", cascade="all, delete-orphan")
    maintenance_records = db.relationship("MaintenanceRecord", back_populates="equipment", cascade="all, delete-orphan")
    schedules = db.relationship("MaintenanceSchedule", back_populates="equipment", cascade="all, delete-orphan")
    predictions = db.relationship("FailurePrediction", back_populates="equipment", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_tag": self.equipment_tag,
            "name": self.name,
            "equipment_type": self.equipment_type,
            "plant_area_id": self.plant_area_id,
            "plant_area_name": self.plant_area.name if self.plant_area else None,
            "description": self.description,
            "operating_status": self.operating_status,
            "installation_date": self.installation_date.isoformat() if self.installation_date else None,
            "maintenance_info": self.maintenance_info,
            "is_active": self.is_active,
            "sensor_count": len(self.sensors) if self.sensors else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
