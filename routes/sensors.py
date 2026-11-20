"""
Sensor Definitions, Configurable Thresholds, and Telemetry Trends Routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.sensor import SensorDefinition, SensorReading
from models.equipment import Equipment
from models.plant import PlantArea
from models.user import User
from services.auth_service import login_required, roles_required
from services.audit_service import log_action

sensors_bp = Blueprint("sensors", __name__)


@sensors_bp.route("/sensors")
@login_required
def index():
    equipment_id = request.args.get("equipment_id", type=int)
    sensor_type = request.args.get("sensor_type", "")

    query = SensorDefinition.query
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)
    if sensor_type:
        query = query.filter_by(sensor_type=sensor_type)

    sensors = query.join(Equipment).order_by(Equipment.equipment_tag, SensorDefinition.sensor_type).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()

    return render_template(
        "sensors/index.html",
        sensors=sensors,
        equipment_list=equipment_list,
        sensor_types=SensorDefinition.SENSOR_TYPES,
        selected_equip=equipment_id,
        selected_type=sensor_type,
    )


@sensors_bp.route("/sensors/<int:sensor_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN, User.ROLE_ENGINEER)
def edit(sensor_id):
    sensor = SensorDefinition.query.get_or_404(sensor_id)

    if request.method == "POST":
        try:
            sensor.sensor_name = request.form.get("sensor_name", sensor.sensor_name).strip()
            sensor.unit = request.form.get("unit", sensor.unit).strip()
            sensor.min_acceptable = float(request.form.get("min_acceptable", sensor.min_acceptable))
            sensor.max_acceptable = float(request.form.get("max_acceptable", sensor.max_acceptable))

            w_min = request.form.get("warning_min")
            sensor.warning_min = float(w_min) if w_min not in ("", None) else None

            w_max = request.form.get("warning_max")
            sensor.warning_max = float(w_max) if w_max not in ("", None) else None

            c_min = request.form.get("critical_min")
            sensor.critical_min = float(c_min) if c_min not in ("", None) else None

            c_max = request.form.get("critical_max")
            sensor.critical_max = float(c_max) if c_max not in ("", None) else None

            sensor.is_enabled = request.form.get("is_enabled") == "on"

            db.session.commit()
            log_action("UPDATE_SENSOR_THRESHOLDS", "SensorDefinition", sensor.id, f"Thresholds updated for {sensor.sensor_name}")
            flash(f"Thresholds for '{sensor.sensor_name}' on {sensor.equipment.equipment_tag} saved.", "success")
            return redirect(url_for("sensors.index", equipment_id=sensor.equipment_id))
        except ValueError as e:
            flash(f"Invalid numeric input for thresholds: {e}", "danger")

    return render_template("sensors/form.html", sensor=sensor)


@sensors_bp.route("/sensors/trends")
@login_required
def trends():
    plant_areas = PlantArea.query.filter_by(is_active=True).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    return render_template(
        "sensors/trends.html",
        plant_areas=plant_areas,
        equipment_list=equipment_list,
        sensor_types=SensorDefinition.SENSOR_TYPES,
    )


@sensors_bp.route("/api/sensors/readings")
@login_required
def api_readings():
    """Paginated or latest readings endpoint."""
    equipment_id = request.args.get("equipment_id", type=int)
    sensor_type = request.args.get("sensor_type", "")
    limit = min(request.args.get("limit", 50, type=int), 200)

    query = SensorReading.query
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)
    if sensor_type:
        query = query.filter_by(sensor_type=sensor_type)

    readings = query.order_by(SensorReading.recorded_at.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in readings])
