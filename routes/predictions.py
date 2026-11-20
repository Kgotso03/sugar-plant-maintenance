"""
Machine Learning Predictive Failure Intelligence Routes.
Includes evaluation metrics, risk categories, confusion matrix, and feature importances.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.prediction import FailurePrediction
from models.equipment import Equipment
from models.user import User
from services.auth_service import login_required, roles_required
from services.prediction_engine import PredictionEngine
from ml.evaluate_model import get_model_evaluation_metrics
from ml.train_model import train_and_save_model
from services.audit_service import log_action

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/predictions")
@login_required
def index():
    risk_filter = request.args.get("risk", "")
    equipment_id = request.args.get("equipment_id", type=int)

    query = FailurePrediction.query
    if risk_filter:
        query = query.filter_by(risk_category=risk_filter)
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)

    predictions = query.order_by(FailurePrediction.prediction_time.desc()).limit(100).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    metrics = get_model_evaluation_metrics()

    return render_template(
        "predictions/index.html",
        predictions=predictions,
        equipment_list=equipment_list,
        metrics=metrics,
        selected_risk=risk_filter,
        selected_equip=equipment_id,
    )


@predictions_bp.route("/api/predictions/run", methods=["POST"])
@login_required
def run_predictions():
    """Runs fresh ML failure risk estimation across active equipment."""
    data = request.get_json() or {}
    equipment_id = data.get("equipment_id")

    if equipment_id:
        equip = Equipment.query.get_or_404(equipment_id)
        pred = PredictionEngine.predict_equipment(equip, persist=True)
        results = [pred.to_dict()]
    else:
        preds = PredictionEngine.predict_all_active_equipment()
        results = [p.to_dict() for p in preds]

    log_action("RUN_ML_PREDICTIONS", "FailurePrediction", None, f"Generated {len(results)} ML risk forecasts")
    return jsonify({"success": True, "count": len(results), "predictions": results})


@predictions_bp.route("/api/predictions/retrain", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN, User.ROLE_ENGINEER)
def retrain_model():
    """Retrains the Random Forest ensemble on freshly synthesized telemetry."""
    try:
        model, metrics = train_and_save_model()
        # Reset cached model instance in prediction engine
        PredictionEngine._model = model
        log_action("RETRAIN_ML_MODEL", "MLModel", None, f"Retrained RF model. Accuracy: {metrics['overall_accuracy']:.2%}")
        return jsonify({"success": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
