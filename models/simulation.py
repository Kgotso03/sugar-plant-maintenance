from datetime import datetime, timezone
from extensions import db


class SimulationRun(db.Model):
    __tablename__ = "simulation_runs"

    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_STOPPED = "stopped"

    SCENARIO_NORMAL = "normal"
    SCENARIO_CONVEYOR_MALFUNCTION = "conveyor_malfunction"
    SCENARIO_CONVEYOR_BELT_STOPPED_MOTOR_RUNNING = "conveyor_belt_stopped_motor_running"
    SCENARIO_HIGH_TEMPERATURE = "high_temperature"
    SCENARIO_LOW_TEMPERATURE = "low_temperature"
    SCENARIO_EXCESSIVE_VIBRATION = "excessive_vibration"
    SCENARIO_HIGH_PRESSURE = "high_pressure"
    SCENARIO_LOW_PRESSURE = "low_pressure"
    SCENARIO_HIGH_MOTOR_CURRENT = "high_motor_current"
    SCENARIO_REDUCED_MOTOR_SPEED = "reduced_motor_speed"
    SCENARIO_GRADUAL_DEGRADATION = "gradual_degradation"
    SCENARIO_MULTIPLE_FAULTS = "multiple_faults"

    SCENARIOS = {
        SCENARIO_NORMAL: "Normal Equipment Operation",
        SCENARIO_CONVEYOR_MALFUNCTION: "Conveyor Belt Malfunction",
        SCENARIO_CONVEYOR_BELT_STOPPED_MOTOR_RUNNING: "Conveyor Belt Stopped While Motor Running",
        SCENARIO_HIGH_TEMPERATURE: "High Temperature",
        SCENARIO_LOW_TEMPERATURE: "Low Temperature",
        SCENARIO_EXCESSIVE_VIBRATION: "Excessive Vibration",
        SCENARIO_HIGH_PRESSURE: "Abnormally High Pressure",
        SCENARIO_LOW_PRESSURE: "Abnormally Low Pressure",
        SCENARIO_HIGH_MOTOR_CURRENT: "High Motor Current",
        SCENARIO_REDUCED_MOTOR_SPEED: "Reduced Motor Speed",
        SCENARIO_GRADUAL_DEGRADATION: "Gradual Equipment Degradation",
        SCENARIO_MULTIPLE_FAULTS: "Multiple Simultaneous Abnormal Readings",
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    scenario = db.Column(db.String(80), default=SCENARIO_NORMAL, nullable=False)
    status = db.Column(db.String(30), default=STATUS_STOPPED, nullable=False)
    speed_factor = db.Column(db.Float, default=1.0, nullable=False)
    selected_equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    readings = db.relationship("SensorReading", back_populates="simulation_run")
    alerts = db.relationship("FaultAlert", back_populates="simulation_run")
    equipment = db.relationship("Equipment")
    created_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "scenario": self.scenario,
            "scenario_name": self.SCENARIOS.get(self.scenario, self.scenario),
            "status": self.status,
            "speed_factor": self.speed_factor,
            "selected_equipment_id": self.selected_equipment_id,
            "selected_equipment_tag": self.equipment.equipment_tag if self.equipment else "All Equipment",
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
