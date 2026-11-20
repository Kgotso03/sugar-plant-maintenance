"""
Equipment Management and Asset Telemetry Detail Routes.
"""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.equipment import Equipment
from models.plant import PlantArea
from models.sensor import SensorDefinition, SensorReading
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from models.user import User
from services.auth_service import login_required, roles_required
from services.audit_service import log_action

equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.route("/equipment")
@login_required
def index():
    plant_area_id = request.args.get("plant_area_id", type=int)
    equip_type = request.args.get("equipment_type", "")
    status = request.args.get("status", "")

    query = Equipment.query
    if plant_area_id:
        query = query.filter_by(plant_area_id=plant_area_id)
    if equip_type:
        query = query.filter_by(equipment_type=equip_type)
    if status:
        query = query.filter_by(operating_status=status)

    equipment_list = query.order_by(Equipment.equipment_tag).all()
    plant_areas = PlantArea.query.filter_by(is_active=True).all()

    return render_template(
        "equipment/index.html",
        equipment_list=equipment_list,
        plant_areas=plant_areas,
        equipment_types=Equipment.EQUIPMENT_TYPES,
        selected_area=plant_area_id,
        selected_type=equip_type,
        selected_status=status,
    )


@equipment_bp.route("/equipment/new", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def create():
    plant_areas = PlantArea.query.filter_by(is_active=True).all()

    if request.method == "POST":
        tag = request.form.get("equipment_tag", "").strip().upper()
        name = request.form.get("name", "").strip()
        equipment_type = request.form.get("equipment_type", "")
        plant_area_id = request.form.get("plant_area_id", type=int)
        description = request.form.get("description", "").strip()
        operating_status = request.form.get("operating_status", Equipment.STATUS_RUNNING)
        installation_date_str = request.form.get("installation_date")
        maintenance_info = request.form.get("maintenance_info", "").strip()

        if not tag or not name or not equipment_type or not plant_area_id:
            flash("Tag, Name, Equipment Type, and Plant Area are required.", "danger")
            return render_template(
                "equipment/form.html",
                equipment=None,
                plant_areas=plant_areas,
                equipment_types=Equipment.EQUIPMENT_TYPES,
            )

        if Equipment.query.filter_by(equipment_tag=tag).first():
            flash(f"Equipment with Tag '{tag}' already exists.", "danger")
            return render_template(
                "equipment/form.html",
                equipment=None,
                plant_areas=plant_areas,
                equipment_types=Equipment.EQUIPMENT_TYPES,
            )

        installation_date = None
        if installation_date_str:
            try:
                installation_date = datetime.strptime(installation_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        equip = Equipment(
            equipment_tag=tag,
            name=name,
            equipment_type=equipment_type,
            plant_area_id=plant_area_id,
            description=description,
            operating_status=operating_status,
            installation_date=installation_date,
            maintenance_info=maintenance_info,
            is_active=True,
        )
        db.session.add(equip)
        db.session.flush()

        # Seed default essential sensors for newly added equipment
        default_sensors = [
            ("temperature", f"{name} Temperature", "°C", 10.0, 95.0, 30.0, 75.0, 20.0, 85.0),
            ("vibration", f"{name} Vibration", "mm/s", 0.0, 15.0, 0.8, 5.0, 0.4, 8.0),
            ("motor_current", f"{name} Motor Current", "A", 0.0, 150.0, 30.0, 120.0, 15.0, 140.0),
        ]
        for stype, sname, unit, min_acc, max_acc, w_min, w_max, c_min, c_max in default_sensors:
            sdef = SensorDefinition(
                equipment_id=equip.id,
                sensor_type=stype,
                sensor_name=sname,
                unit=unit,
                min_acceptable=min_acc,
                max_acceptable=max_acc,
                warning_min=w_min,
                warning_max=w_max,
                critical_min=c_min,
                critical_max=c_max,
                is_enabled=True,
            )
            db.session.add(sdef)

        db.session.commit()
        log_action("CREATE_EQUIPMENT", "Equipment", equip.id, f"Created equipment {equip.equipment_tag}")
        flash(f"Equipment '{equip.equipment_tag} - {equip.name}' created with default sensors.", "success")
        return redirect(url_for("equipment.detail", equip_id=equip.id))

    return render_template(
        "equipment/form.html",
        equipment=None,
        plant_areas=plant_areas,
        equipment_types=Equipment.EQUIPMENT_TYPES,
    )


@equipment_bp.route("/equipment/<int:equip_id>")
@login_required
def detail(equip_id):
    equip = Equipment.query.get_or_404(equip_id)

    # Latest readings per sensor
    sensors = SensorDefinition.query.filter_by(equipment_id=equip.id).all()
    latest_readings = {}
    for s in sensors:
        latest = (
            SensorReading.query.filter_by(sensor_definition_id=s.id)
            .order_by(SensorReading.id.desc())
            .first()
        )
        latest_readings[s.id] = latest

    active_alerts = (
        FaultAlert.query.filter_by(equipment_id=equip.id)
        .filter(FaultAlert.status != FaultAlert.STATUS_RESOLVED)
        .order_by(FaultAlert.created_at.desc())
        .all()
    )

    work_orders = (
        WorkOrder.query.filter_by(equipment_id=equip.id)
        .order_by(WorkOrder.created_at.desc())
        .limit(10)
        .all()
    )

    maintenance_records = (
        MaintenanceRecord.query.filter_by(equipment_id=equip.id)
        .order_by(MaintenanceRecord.performed_at.desc())
        .limit(10)
        .all()
    )

    predictions = (
        FailurePrediction.query.filter_by(equipment_id=equip.id)
        .order_by(FailurePrediction.prediction_time.desc())
        .limit(5)
        .all()
    )

    schedules = (
        MaintenanceSchedule.query.filter_by(equipment_id=equip.id, is_active=True)
        .order_by(MaintenanceSchedule.next_due_date.asc())
        .all()
    )

    return render_template(
        "equipment/detail.html",
        equipment=equip,
        sensors=sensors,
        latest_readings=latest_readings,
        active_alerts=active_alerts,
        work_orders=work_orders,
        maintenance_records=maintenance_records,
        predictions=predictions,
        schedules=schedules,
    )


@equipment_bp.route("/equipment/<int:equip_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def edit(equip_id):
    equip = Equipment.query.get_or_404(equip_id)
    plant_areas = PlantArea.query.filter_by(is_active=True).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        equipment_type = request.form.get("equipment_type", "")
        plant_area_id = request.form.get("plant_area_id", type=int)
        description = request.form.get("description", "").strip()
        operating_status = request.form.get("operating_status", equip.operating_status)
        installation_date_str = request.form.get("installation_date")
        maintenance_info = request.form.get("maintenance_info", "").strip()

        if not name or not equipment_type or not plant_area_id:
            flash("Name, Equipment Type, and Plant Area are required.", "danger")
            return render_template(
                "equipment/form.html",
                equipment=equip,
                plant_areas=plant_areas,
                equipment_types=Equipment.EQUIPMENT_TYPES,
            )

        if installation_date_str:
            try:
                equip.installation_date = datetime.strptime(installation_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        equip.name = name
        equip.equipment_type = equipment_type
        equip.plant_area_id = plant_area_id
        equip.description = description
        equip.operating_status = operating_status
        equip.maintenance_info = maintenance_info

        db.session.commit()
        log_action("EDIT_EQUIPMENT", "Equipment", equip.id, f"Updated equipment {equip.equipment_tag}")
        flash(f"Equipment '{equip.equipment_tag}' updated successfully.", "success")
        return redirect(url_for("equipment.detail", equip_id=equip.id))

    return render_template(
        "equipment/form.html",
        equipment=equip,
        plant_areas=plant_areas,
        equipment_types=Equipment.EQUIPMENT_TYPES,
    )


@equipment_bp.route("/equipment/<int:equip_id>/toggle", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def toggle(equip_id):
    equip = Equipment.query.get_or_404(equip_id)
    equip.is_active = not equip.is_active
    db.session.commit()
    log_action("TOGGLE_EQUIPMENT", "Equipment", equip.id, f"Equipment {equip.equipment_tag} active set to {equip.is_active}")
    flash(f"Equipment '{equip.equipment_tag}' status set to {'Active' if equip.is_active else 'Deactivated'}.", "info")
    return redirect(url_for("equipment.index"))


@equipment_bp.route("/api/equipment/<int:equip_id>/telemetry")
@login_required
def api_telemetry(equip_id):
    """Returns recent sensor readings history for live charts on detail page."""
    readings = (
        SensorReading.query.filter_by(equipment_id=equip_id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(60)
        .all()
    )
    readings.reverse()
    return jsonify([r.to_dict() for r in readings])
