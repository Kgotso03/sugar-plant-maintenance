"""
Machine Learning Failure Risk Prediction Service.
Uses trained Random Forest ensemble to estimate failure risk from live sensor telemetry.
Provides contributing factor attribution and recommended inspection actions.
NOTICE: Advisory predictive maintenance only. Does NOT issue automated machine shutdown commands.
"""
import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from extensions import db
from models.equipment import Equipment
from models.sensor import SensorReading, SensorDefinition
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from ml.train_model import MODEL_PATH, FEATURE_NAMES, TARGET_LABELS, train_and_save_model


class PredictionEngine:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if not os.path.exists(MODEL_PATH):
                cls._model, _ = train_and_save_model()
            else:
                try:
                    cls._model = joblib.load(MODEL_PATH)
                except Exception:
                    cls._model, _ = train_and_save_model()
        return cls._model

    @classmethod
    def extract_equipment_features(cls, equipment: Equipment) -> tuple[dict, list[str]]:
        """
        Extracts feature values and identifies sensor indicators from recent telemetry.
        """
        # Fetch latest readings for each sensor type
        recent_readings = (
            SensorReading.query.filter_by(equipment_id=equipment.id)
            .order_by(SensorReading.id.desc())
            .limit(30)
            .all()
        )

        by_type = {}
        for r in recent_readings:
            by_type.setdefault(r.sensor_type, []).append(r.value)

        def get_stat(stype, default_val=50.0):
            vals = by_type.get(stype, [])
            if not vals:
                return default_val, 0.0
            curr = vals[0]
            avg = sum(vals[:5]) / len(vals[:5])
            trend = (vals[0] - vals[-1]) / max(1, len(vals)) if len(vals) > 1 else 0.0
            return curr, trend

        temp_val, temp_trend = get_stat(SensorDefinition.TYPE_TEMPERATURE, 55.0)
        vib_val, vib_trend = get_stat(SensorDefinition.TYPE_VIBRATION, 2.0)
        press_val, press_trend = get_stat(SensorDefinition.TYPE_PRESSURE, 38.0)
        curr_val, _ = get_stat(SensorDefinition.TYPE_MOTOR_CURRENT, 80.0)
        speed_val, _ = get_stat(SensorDefinition.TYPE_MOTOR_SPEED, 1480.0)
        belt_val, _ = get_stat(SensorDefinition.TYPE_BELT_SPEED, 1.8)

        # Recent alerts count
        alert_count = (
            FaultAlert.query.filter_by(equipment_id=equipment.id)
            .filter(FaultAlert.status.in_([FaultAlert.STATUS_ACTIVE, FaultAlert.STATUS_ACKNOWLEDGED]))
            .count()
        )

        operating_hours = 2500.0
        if equipment.installation_date:
            days = (datetime.now(timezone.utc).date() - equipment.installation_date).days
            operating_hours = min(15000.0, max(100.0, days * 16.0))

        features = {
            "temperature": float(temp_val),
            "temp_trend": float(temp_trend),
            "vibration": float(vib_val),
            "vibration_trend": float(vib_trend),
            "pressure": float(press_val),
            "pressure_trend": float(press_trend),
            "motor_current": float(curr_val),
            "motor_speed": float(speed_val),
            "conveyor_speed": float(belt_val),
            "operating_hours": float(operating_hours),
            "recent_alert_count": int(alert_count),
        }

        # Contributing indicator explanations
        factors = []
        if vib_val > 5.0 or vib_trend > 0.4:
            factors.append(f"Elevated vibration ({vib_val:.1f} mm/s, trend +{vib_trend:.2f} mm/s/step)")
        if temp_val > 75.0 or temp_trend > 1.0:
            factors.append(f"Thermal elevation ({temp_val:.1f} C, trend +{temp_trend:.2f} C/step)")
        if curr_val > 120.0:
            factors.append(f"High motor current draw ({curr_val:.1f} A)")
        if alert_count > 0:
            factors.append(f"{alert_count} active/unresolved threshold alert(s)")
        if not factors:
            factors.append("All primary sensor channels operating within nominal range")

        return features, factors

    @classmethod
    def predict_equipment(cls, equipment: Equipment, persist: bool = True) -> FailurePrediction:
        """
        Runs failure risk prediction for given equipment and creates a FailurePrediction record.
        """
        model = cls.get_model()
        features, factors = cls.extract_equipment_features(equipment)

        df = pd.DataFrame([features])[FEATURE_NAMES]
        pred_class = model.predict(df)[0]
        probs = model.predict_proba(df)[0]

        # Probabilities order: [low, medium, high]
        category = TARGET_LABELS.get(pred_class, "low")
        # Risk score is weighted probability (medium * 0.5 + high * 1.0)
        risk_score = float(probs[1] * 0.5 + probs[2] * 1.0) if len(probs) == 3 else float(probs[pred_class])

        # Formulate recommended inspection actions
        if category == "high":
            recommended_action = (
                f"HIGH FAILURE PROBABILITY ({risk_score*100:.1f}%): Immediate engineering inspection recommended. "
                f"Check mechanical alignment, lubrication contamination, and bearing degradation on {equipment.equipment_tag}."
            )
        elif category == "medium":
            recommended_action = (
                f"MODERATE FAILURE RISK ({risk_score*100:.1f}%): Schedule preventive inspection on next shift. "
                f"Inspect temperature gradients and monitor vibration trend for {equipment.equipment_tag}."
            )
        else:
            recommended_action = (
                f"LOW RISK ({(1-risk_score)*100:.1f}% healthy): Routine monitoring. "
                f"Continue regular scheduled maintenance rounds."
            )

        prediction = FailurePrediction(
            equipment_id=equipment.id,
            risk_category=category,
            risk_score=risk_score,
            recommended_action=recommended_action,
            model_version="RandomForest-v1.0",
            is_simulated=True,
            prediction_time=datetime.now(timezone.utc),
        )
        prediction.set_factors(factors)

        if persist:
            db.session.add(prediction)
            db.session.commit()

        return prediction

    @classmethod
    def predict_all_active_equipment(cls) -> list[FailurePrediction]:
        """Runs predictions across all registered active assets."""
        active_eq = Equipment.query.filter_by(is_active=True).all()
        predictions = []
        for eq in active_eq:
            pred = cls.predict_equipment(eq, persist=True)
            predictions.append(pred)
        return predictions
