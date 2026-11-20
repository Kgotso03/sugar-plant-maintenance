from datetime import datetime, timezone
from extensions import db


class FaultAlert(db.Model):
    __tablename__ = "fault_alerts"

    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"

    STATUS_ACTIVE = "active"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_RESOLVED = "resolved"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    sensor_definition_id = db.Column(db.Integer, db.ForeignKey("sensor_definitions.id"), nullable=True, index=True)
    simulation_run_id = db.Column(db.Integer, db.ForeignKey("simulation_runs.id"), nullable=True, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    observed_value = db.Column(db.Float, nullable=False)
    configured_limit = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default=SEVERITY_WARNING, index=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE, index=True)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    last_occurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    equipment = db.relationship("Equipment", back_populates="alerts")
    sensor_definition = db.relationship("SensorDefinition", back_populates="alerts")
    simulation_run = db.relationship("SimulationRun", back_populates="alerts")
    acknowledged_by = db.relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id])
    work_orders = db.relationship("WorkOrder", back_populates="alert")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "plant_area": self.equipment.plant_area.name if self.equipment and self.equipment.plant_area else None,
            "sensor_type": self.sensor_type,
            "observed_value": round(self.observed_value, 2),
            "configured_limit": round(self.configured_limit, 2),
            "severity": self.severity,
            "description": self.description,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by.username if self.acknowledged_by else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_by": self.resolved_by.username if self.resolved_by else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "comments": self.comments,
            "last_occurred_at": self.last_occurred_at.isoformat() if self.last_occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
