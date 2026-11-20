from datetime import datetime, timezone
from extensions import db


class SensorDefinition(db.Model):
    __tablename__ = "sensor_definitions"

    TYPE_TEMPERATURE = "temperature"
    TYPE_VIBRATION = "vibration"
    TYPE_PRESSURE = "pressure"
    TYPE_MOTOR_CURRENT = "motor_current"
    TYPE_BELT_SPEED = "belt_speed"
    TYPE_MOTOR_SPEED = "motor_speed"

    SENSOR_TYPES = [
        TYPE_TEMPERATURE,
        TYPE_VIBRATION,
        TYPE_PRESSURE,
        TYPE_MOTOR_CURRENT,
        TYPE_BELT_SPEED,
        TYPE_MOTOR_SPEED,
    ]

    UNITS = {
        TYPE_TEMPERATURE: "°C",
        TYPE_VIBRATION: "mm/s",
        TYPE_PRESSURE: "bar",
        TYPE_MOTOR_CURRENT: "A",
        TYPE_BELT_SPEED: "m/s",
        TYPE_MOTOR_SPEED: "RPM",
    }

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    sensor_name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    min_acceptable = db.Column(db.Float, default=0.0, nullable=False)
    max_acceptable = db.Column(db.Float, default=100.0, nullable=False)
    warning_min = db.Column(db.Float, nullable=True)
    warning_max = db.Column(db.Float, nullable=True)
    critical_min = db.Column(db.Float, nullable=True)
    critical_max = db.Column(db.Float, nullable=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    equipment = db.relationship("Equipment", back_populates="sensors")
    readings = db.relationship("SensorReading", back_populates="sensor_definition", cascade="all, delete-orphan")
    alerts = db.relationship("FaultAlert", back_populates="sensor_definition")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "sensor_type": self.sensor_type,
            "sensor_name": self.sensor_name,
            "unit": self.unit,
            "min_acceptable": self.min_acceptable,
            "max_acceptable": self.max_acceptable,
            "warning_min": self.warning_min,
            "warning_max": self.warning_max,
            "critical_min": self.critical_min,
            "critical_max": self.critical_max,
            "is_enabled": self.is_enabled,
        }


class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    STATUS_NORMAL = "normal"
    STATUS_WARNING = "warning"
    STATUS_CRITICAL = "critical"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    sensor_definition_id = db.Column(db.Integer, db.ForeignKey("sensor_definitions.id"), nullable=False, index=True)
    simulation_run_id = db.Column(db.Integer, db.ForeignKey("simulation_runs.id"), nullable=True, index=True)
    sensor_type = db.Column(db.String(50), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default=STATUS_NORMAL, nullable=False)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    equipment = db.relationship("Equipment", back_populates="readings")
    sensor_definition = db.relationship("SensorDefinition", back_populates="readings")
    simulation_run = db.relationship("SimulationRun", back_populates="readings")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "sensor_definition_id": self.sensor_definition_id,
            "sensor_type": self.sensor_type,
            "value": round(self.value, 2),
            "unit": self.unit,
            "status": self.status,
            "is_simulated": self.is_simulated,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
