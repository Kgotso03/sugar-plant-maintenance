import json
from datetime import datetime, timezone
from extensions import db


class FailurePrediction(db.Model):
    __tablename__ = "failure_predictions"

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    risk_category = db.Column(db.String(20), nullable=False, default=RISK_LOW, index=True)
    risk_score = db.Column(db.Float, nullable=False)  # 0.0 to 1.0 probability
    contributing_factors = db.Column(db.Text, nullable=True)  # JSON formatted factors
    recommended_action = db.Column(db.Text, nullable=False)
    model_version = db.Column(db.String(50), default="RandomForest-v1.0", nullable=False)
    is_simulated = db.Column(db.Boolean, default=True, nullable=False)
    prediction_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    equipment = db.relationship("Equipment", back_populates="predictions")

    def get_factors(self):
        if not self.contributing_factors:
            return []
        try:
            return json.loads(self.contributing_factors)
        except Exception:
            return []

    def set_factors(self, factors_list):
        self.contributing_factors = json.dumps(factors_list)

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "plant_area": self.equipment.plant_area.name if self.equipment and self.equipment.plant_area else None,
            "risk_category": self.risk_category,
            "risk_score": round(self.risk_score, 4),
            "risk_percentage": round(self.risk_score * 100, 1),
            "contributing_factors": self.get_factors(),
            "recommended_action": self.recommended_action,
            "model_version": self.model_version,
            "is_simulated": self.is_simulated,
            "prediction_time": self.prediction_time.isoformat() if self.prediction_time else None,
        }
