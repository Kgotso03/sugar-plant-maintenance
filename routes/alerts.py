"""
Fault Alerts Management and Investigation Routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.alert import FaultAlert
from models.equipment import Equipment
from models.plant import PlantArea
from models.user import User
from services.auth_service import login_required, roles_required, get_current_user
from services.alert_service import acknowledge_alert, resolve_alert, add_comment

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
@login_required
def index():
    status = request.args.get("status", "")
    severity = request.args.get("severity", "")
    equipment_id = request.args.get("equipment_id", type=int)
    plant_area_id = request.args.get("plant_area_id", type=int)

    query = FaultAlert.query
    if status:
        query = query.filter_by(status=status)
    if severity:
        query = query.filter_by(severity=severity)
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)
    if plant_area_id:
        query = query.join(Equipment).filter(Equipment.plant_area_id == plant_area_id)

    alerts = query.order_by(FaultAlert.last_occurred_at.desc()).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    plant_areas = PlantArea.query.filter_by(is_active=True).all()

    return render_template(
        "alerts/index.html",
        alerts=alerts,
        equipment_list=equipment_list,
        plant_areas=plant_areas,
        selected_status=status,
        selected_severity=severity,
        selected_equip=equipment_id,
        selected_area=plant_area_id,
    )


@alerts_bp.route("/api/alerts/active")
@login_required
def api_active():
    active_alerts = (
        FaultAlert.query.filter(FaultAlert.status.in_([FaultAlert.STATUS_ACTIVE, FaultAlert.STATUS_ACKNOWLEDGED]))
        .order_by(FaultAlert.last_occurred_at.desc())
        .limit(20)
        .all()
    )
    return jsonify([a.to_dict() for a in active_alerts])


@alerts_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@login_required
def acknowledge(alert_id):
    user = get_current_user()
    comment = request.form.get("comment", "").strip() or "Acknowledged from alerts dashboard."
    acknowledge_alert(alert_id=alert_id, user_id=user.id, comment=comment)
    flash(f"Alert #{alert_id} has been acknowledged.", "info")
    return redirect(request.referrer or url_for("alerts.index"))


@alerts_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def resolve(alert_id):
    user = get_current_user()
    comment = request.form.get("comment", "").strip() or "Resolved from alerts dashboard."
    resolve_alert(alert_id=alert_id, user_id=user.id, comment=comment)
    flash(f"Alert #{alert_id} has been marked as resolved.", "success")
    return redirect(request.referrer or url_for("alerts.index"))


@alerts_bp.route("/alerts/<int:alert_id>/comment", methods=["POST"])
@login_required
def comment(alert_id):
    user = get_current_user()
    note = request.form.get("comment", "").strip()
    if note:
        add_comment(alert_id=alert_id, user_id=user.id, comment=note)
        flash("Comment recorded on alert.", "success")
    return redirect(request.referrer or url_for("alerts.index"))
