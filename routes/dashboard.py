"""
Industrial Dashboard and Real-Time Telemetry Analytics.
"""
from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import func
from extensions import db
from models.equipment import Equipment
from models.plant import PlantArea
from models.sensor import SensorReading, SensorDefinition
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from services.auth_service import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    plant_areas = PlantArea.query.filter_by(is_active=True).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    return render_template(
        "dashboard/index.html",
        plant_areas=plant_areas,
        equipment_list=equipment_list,
    )


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def api_stats():
    """Returns dynamic KPI metrics calculated live from database records."""
    total_equipment = Equipment.query.filter_by(is_active=True).count()

    # Active alert counts
    critical_alerts_count = (
        FaultAlert.query.filter_by(status=FaultAlert.STATUS_ACTIVE, severity=FaultAlert.SEVERITY_CRITICAL).count()
    )
    warning_alerts_count = (
        FaultAlert.query.filter_by(status=FaultAlert.STATUS_ACTIVE, severity=FaultAlert.SEVERITY_WARNING).count()
    )

    # Equipment condition breakdown
    # Any equipment with an active critical alert is in critical state
    critical_equip_ids = [
        r[0]
        for r in db.session.query(FaultAlert.equipment_id)
        .filter(FaultAlert.status.in_([FaultAlert.STATUS_ACTIVE, FaultAlert.STATUS_ACKNOWLEDGED]), FaultAlert.severity == FaultAlert.SEVERITY_CRITICAL)
        .distinct()
        .all()
    ]
    warning_equip_ids = [
        r[0]
        for r in db.session.query(FaultAlert.equipment_id)
        .filter(
            FaultAlert.status.in_([FaultAlert.STATUS_ACTIVE, FaultAlert.STATUS_ACKNOWLEDGED]),
            FaultAlert.severity == FaultAlert.SEVERITY_WARNING,
            ~FaultAlert.equipment_id.in_(critical_equip_ids) if critical_equip_ids else True,
        )
        .distinct()
        .all()
    ]

    equipment_critical = len(critical_equip_ids)
    equipment_warning = len(warning_equip_ids)
    equipment_normal = max(0, total_equipment - equipment_critical - equipment_warning)

    # ML Predictions High Risk
    latest_pred_subq = (
        db.session.query(
            FailurePrediction.equipment_id,
            func.max(FailurePrediction.id).label("max_id"),
        )
        .group_by(FailurePrediction.equipment_id)
        .subquery()
    )
    high_risk_predictions = (
        db.session.query(FailurePrediction)
        .join(latest_pred_subq, FailurePrediction.id == latest_pred_subq.c.max_id)
        .filter(FailurePrediction.risk_category == FailurePrediction.RISK_HIGH)
        .count()
    )

    # Work orders & schedules
    open_work_orders = WorkOrder.query.filter(
        WorkOrder.status.in_([WorkOrder.STATUS_OPEN, WorkOrder.STATUS_ASSIGNED, WorkOrder.STATUS_IN_PROGRESS])
    ).count()

    today = date.today()
    overdue_tasks = MaintenanceSchedule.query.filter(
        MaintenanceSchedule.is_active == True,
        MaintenanceSchedule.next_due_date < today,
    ).count()

    # Recent alerts & activities
    recent_alerts = [
        a.to_dict()
        for a in FaultAlert.query.order_by(FaultAlert.last_occurred_at.desc()).limit(5).all()
    ]
    recent_maintenance = [
        m.to_dict()
        for m in MaintenanceRecord.query.order_by(MaintenanceRecord.performed_at.desc()).limit(5).all()
    ]

    return jsonify({
        "total_equipment": total_equipment,
        "equipment_normal": equipment_normal,
        "equipment_warning": equipment_warning,
        "equipment_critical": equipment_critical,
        "active_critical_alerts": critical_alerts_count,
        "active_warning_alerts": warning_alerts_count,
        "high_risk_predictions": high_risk_predictions,
        "open_work_orders": open_work_orders,
        "overdue_tasks": overdue_tasks,
        "recent_alerts": recent_alerts,
        "recent_maintenance": recent_maintenance,
    })


@dashboard_bp.route("/api/dashboard/charts")
@login_required
def api_charts():
    """Generates Chart.js datasets from actual database records."""
    plant_area_id = request.args.get("plant_area_id", type=int)
    equipment_id = request.args.get("equipment_id", type=int)

    # 1. Telemetry Trends (last 20 readings for temperature, vibration, pressure, current)
    query = SensorReading.query
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)
    elif plant_area_id:
        equip_ids = [e.id for e in Equipment.query.filter_by(plant_area_id=plant_area_id).all()]
        query = query.filter(SensorReading.equipment_id.in_(equip_ids))

    def get_trend_data(sensor_type):
        rows = (
            query.filter_by(sensor_type=sensor_type)
            .order_by(SensorReading.recorded_at.desc())
            .limit(20)
            .all()
        )
        rows.reverse()
        labels = [r.recorded_at.strftime("%H:%M:%S") for r in rows]
        values = [round(r.value, 2) for r in rows]
        return {"labels": labels, "values": values}

    temp_trend = get_trend_data(SensorDefinition.TYPE_TEMPERATURE)
    vib_trend = get_trend_data(SensorDefinition.TYPE_VIBRATION)
    press_trend = get_trend_data(SensorDefinition.TYPE_PRESSURE)
    curr_trend = get_trend_data(SensorDefinition.TYPE_MOTOR_CURRENT)

    # 2. Alerts by Severity
    severity_counts = (
        db.session.query(FaultAlert.severity, func.count(FaultAlert.id))
        .group_by(FaultAlert.severity)
        .all()
    )
    sev_map = dict(severity_counts)
    alerts_by_severity = {
        "labels": ["Warning", "Critical"],
        "values": [sev_map.get("warning", 0), sev_map.get("critical", 0)],
    }

    # 3. Faults by Plant Area
    area_faults = (
        db.session.query(PlantArea.name, func.count(FaultAlert.id))
        .join(Equipment, Equipment.plant_area_id == PlantArea.id)
        .join(FaultAlert, FaultAlert.equipment_id == Equipment.id)
        .group_by(PlantArea.name)
        .all()
    )
    faults_by_area = {
        "labels": [r[0] for r in area_faults] if area_faults else ["No Recorded Faults"],
        "values": [r[1] for r in area_faults] if area_faults else [0],
    }

    # 4. Work Orders by Status
    wo_counts = (
        db.session.query(WorkOrder.status, func.count(WorkOrder.id))
        .group_by(WorkOrder.status)
        .all()
    )
    wo_map = dict(wo_counts)
    wo_status = {
        "labels": ["Open", "Assigned", "In Progress", "Awaiting Parts", "Completed", "Cancelled"],
        "values": [
            wo_map.get(WorkOrder.STATUS_OPEN, 0),
            wo_map.get(WorkOrder.STATUS_ASSIGNED, 0),
            wo_map.get(WorkOrder.STATUS_IN_PROGRESS, 0),
            wo_map.get(WorkOrder.STATUS_AWAITING_PARTS, 0),
            wo_map.get(WorkOrder.STATUS_COMPLETED, 0),
            wo_map.get(WorkOrder.STATUS_CANCELLED, 0),
        ],
    }

    # 5. Failure Risk Categories Breakdown
    latest_pred_subq = (
        db.session.query(
            FailurePrediction.equipment_id,
            func.max(FailurePrediction.id).label("max_id"),
        )
        .group_by(FailurePrediction.equipment_id)
        .subquery()
    )
    risk_counts = (
        db.session.query(FailurePrediction.risk_category, func.count(FailurePrediction.id))
        .join(latest_pred_subq, FailurePrediction.id == latest_pred_subq.c.max_id)
        .group_by(FailurePrediction.risk_category)
        .all()
    )
    risk_map = dict(risk_counts)
    risk_distribution = {
        "labels": ["Low Risk", "Medium Risk", "High Risk"],
        "values": [
            risk_map.get("low", 0),
            risk_map.get("medium", 0),
            risk_map.get("high", 0),
        ],
    }

    return jsonify({
        "temperature_trend": temp_trend,
        "vibration_trend": vib_trend,
        "pressure_trend": press_trend,
        "current_trend": curr_trend,
        "alerts_by_severity": alerts_by_severity,
        "faults_by_area": faults_by_area,
        "work_order_status": wo_status,
        "risk_distribution": risk_distribution,
    })
