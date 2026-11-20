"""
Reports and Data Analytics Export Routes (CSV & Print Views).
Explicitly marks simulated vs user-recorded data.
"""
import io
import csv
from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, render_template, request, make_response, flash
from extensions import db
from models.equipment import Equipment
from models.plant import PlantArea
from models.sensor import SensorReading, SensorDefinition
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from services.auth_service import login_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
@login_required
def index():
    report_type = request.args.get("report_type", "equipment_condition")
    plant_area_id = request.args.get("plant_area_id", type=int)
    equipment_id = request.args.get("equipment_id", type=int)
    date_from_str = request.args.get("date_from", "")
    date_to_str = request.args.get("date_to", "")

    plant_areas = PlantArea.query.filter_by(is_active=True).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()

    data = []
    is_simulated = True

    if report_type == "equipment_condition":
        is_simulated = False
        query = Equipment.query
        if plant_area_id:
            query = query.filter_by(plant_area_id=plant_area_id)
        if equipment_id:
            query = query.filter_by(id=equipment_id)
        data = query.order_by(Equipment.equipment_tag).all()

    elif report_type == "sensor_readings":
        is_simulated = True
        query = SensorReading.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        elif plant_area_id:
            eq_ids = [e.id for e in Equipment.query.filter_by(plant_area_id=plant_area_id).all()]
            query = query.filter(SensorReading.equipment_id.in_(eq_ids))
        data = query.order_by(SensorReading.recorded_at.desc()).limit(200).all()

    elif report_type == "fault_alerts":
        is_simulated = True
        query = FaultAlert.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        elif plant_area_id:
            eq_ids = [e.id for e in Equipment.query.filter_by(plant_area_id=plant_area_id).all()]
            query = query.filter(FaultAlert.equipment_id.in_(eq_ids))
        data = query.order_by(FaultAlert.last_occurred_at.desc()).all()

    elif report_type == "failure_predictions":
        is_simulated = True
        query = FailurePrediction.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        data = query.order_by(FailurePrediction.prediction_time.desc()).limit(100).all()

    elif report_type == "work_orders":
        is_simulated = False
        query = WorkOrder.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        elif plant_area_id:
            eq_ids = [e.id for e in Equipment.query.filter_by(plant_area_id=plant_area_id).all()]
            query = query.filter(WorkOrder.equipment_id.in_(eq_ids))
        data = query.order_by(WorkOrder.created_at.desc()).all()

    elif report_type == "preventive_schedules":
        is_simulated = False
        query = MaintenanceSchedule.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        data = query.order_by(MaintenanceSchedule.next_due_date.asc()).all()

    elif report_type in ("downtime_summary", "maintenance_costs"):
        is_simulated = False
        query = MaintenanceRecord.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        data = query.order_by(MaintenanceRecord.performed_at.desc()).all()

    # Aggregate metrics
    total_downtime = (
        sum(r.estimated_downtime_hours for r in data)
        if report_type in ("downtime_summary", "maintenance_costs")
        else 0.0
    )
    total_cost = (
        sum(r.cost for r in data)
        if report_type in ("downtime_summary", "maintenance_costs")
        else sum(w.maintenance_cost for w in data) if report_type == "work_orders" else 0.0
    )

    return render_template(
        "reports/index.html",
        report_type=report_type,
        data=data,
        is_simulated=is_simulated,
        plant_areas=plant_areas,
        equipment_list=equipment_list,
        selected_area=plant_area_id,
        selected_equip=equipment_id,
        date_from=date_from_str,
        date_to=date_to_str,
        total_downtime=round(total_downtime, 1),
        total_cost=round(total_cost, 2),
    )


@reports_bp.route("/reports/export-csv")
@login_required
def export_csv():
    report_type = request.args.get("report_type", "equipment_condition")
    plant_area_id = request.args.get("plant_area_id", type=int)
    equipment_id = request.args.get("equipment_id", type=int)

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "equipment_condition":
        writer.writerow(["DATA CLASSIFICATION", "ACTUAL RECORDS ENTERED BY USERS"])
        writer.writerow(["Tag", "Name", "Type", "Plant Area", "Status", "Installation Date"])
        query = Equipment.query
        if equipment_id:
            query = query.filter_by(id=equipment_id)
        for eq in query.all():
            writer.writerow([
                eq.equipment_tag,
                eq.name,
                eq.equipment_type,
                eq.plant_area.name if eq.plant_area else "",
                eq.operating_status,
                eq.installation_date.isoformat() if eq.installation_date else "",
            ])

    elif report_type == "sensor_readings":
        writer.writerow(["DATA CLASSIFICATION", "SIMULATED TELEMETRY DATA"])
        writer.writerow(["Timestamp (UTC)", "Equipment Tag", "Sensor Type", "Observed Value", "Unit", "Status"])
        query = SensorReading.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        for r in query.order_by(SensorReading.recorded_at.desc()).limit(1000).all():
            writer.writerow([
                r.recorded_at.isoformat(),
                r.equipment.equipment_tag if r.equipment else "",
                r.sensor_type,
                r.value,
                r.unit,
                r.status,
            ])

    elif report_type == "fault_alerts":
        writer.writerow(["DATA CLASSIFICATION", "SIMULATED FAULT ALERTS"])
        writer.writerow(["Alert ID", "Timestamp", "Equipment Tag", "Sensor Type", "Observed Value", "Configured Limit", "Severity", "Status", "Description"])
        query = FaultAlert.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        for a in query.order_by(FaultAlert.last_occurred_at.desc()).all():
            writer.writerow([
                a.id,
                a.last_occurred_at.isoformat(),
                a.equipment.equipment_tag if a.equipment else "",
                a.sensor_type,
                a.observed_value,
                a.configured_limit,
                a.severity,
                a.status,
                a.description,
            ])

    elif report_type == "work_orders":
        writer.writerow(["DATA CLASSIFICATION", "ACTUAL MAINTENANCE WORK ORDERS"])
        writer.writerow(["WO Number", "Equipment Tag", "Title", "Priority", "Status", "Due Date", "Labor Hours", "Cost", "Completed At"])
        query = WorkOrder.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        for w in query.order_by(WorkOrder.created_at.desc()).all():
            writer.writerow([
                w.work_order_number,
                w.equipment.equipment_tag if w.equipment else "",
                w.title,
                w.priority,
                w.status,
                w.due_date.isoformat() if w.due_date else "",
                w.labor_hours,
                w.maintenance_cost,
                w.completed_at.isoformat() if w.completed_at else "",
            ])

    elif report_type in ("downtime_summary", "maintenance_costs"):
        writer.writerow(["DATA CLASSIFICATION", "EQUIPMENT SERVICE & DOWNTIME HISTORY"])
        writer.writerow(["Date", "Equipment Tag", "Record Type", "Title", "Action Taken", "Labor Hours", "Cost ($)", "Downtime (Hours)"])
        query = MaintenanceRecord.query
        if equipment_id:
            query = query.filter_by(equipment_id=equipment_id)
        for m in query.order_by(MaintenanceRecord.performed_at.desc()).all():
            writer.writerow([
                m.performed_at.isoformat(),
                m.equipment.equipment_tag if m.equipment else "",
                m.record_type,
                m.title,
                m.action_taken,
                m.labor_hours,
                m.cost,
                m.estimated_downtime_hours,
            ])

    filename = f"sugar_plant_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


@reports_bp.route("/reports/print")
@login_required
def print_view():
    report_type = request.args.get("report_type", "equipment_condition")
    equipment_id = request.args.get("equipment_id", type=int)

    query_equip = Equipment.query
    if equipment_id:
        query_equip = query_equip.filter_by(id=equipment_id)
    equipment_list = query_equip.all()

    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).limit(20).all()
    alerts = FaultAlert.query.order_by(FaultAlert.last_occurred_at.desc()).limit(20).all()
    predictions = FailurePrediction.query.order_by(FailurePrediction.prediction_time.desc()).limit(20).all()
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.performed_at.desc()).limit(20).all()

    return render_template(
        "reports/print.html",
        generated_at=datetime.now(timezone.utc),
        equipment_list=equipment_list,
        work_orders=work_orders,
        alerts=alerts,
        predictions=predictions,
        records=records,
    )
