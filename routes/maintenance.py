"""
Maintenance Management Routes: Work Orders, Preventive Schedules, and Repair History.
"""
from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from models.equipment import Equipment
from models.alert import FaultAlert
from models.user import User
from services.auth_service import login_required, roles_required, get_current_user
from services.maintenance_service import (
    create_work_order,
    update_work_order,
    complete_work_order,
    cancel_work_order,
    complete_schedule,
)
from services.audit_service import log_action

maintenance_bp = Blueprint("maintenance", __name__)


# ── Work Orders ─────────────────────────────────────────────────────────────
@maintenance_bp.route("/work-orders")
@login_required
def work_orders():
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    equipment_id = request.args.get("equipment_id", type=int)

    query = WorkOrder.query
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)

    orders = query.order_by(WorkOrder.created_at.desc()).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()

    return render_template(
        "maintenance/work_orders.html",
        work_orders=orders,
        equipment_list=equipment_list,
        statuses=WorkOrder.STATUSES,
        priorities=WorkOrder.PRIORITIES,
        selected_status=status,
        selected_priority=priority,
        selected_equip=equipment_id,
    )


@maintenance_bp.route("/work-orders/new", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN, User.ROLE_ENGINEER)
def create_order():
    user = get_current_user()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    technicians = User.query.filter(User.role.in_([User.ROLE_TECHNICIAN, User.ROLE_ENGINEER]), User.is_active == True).all()

    prefill_equipment_id = request.args.get("equipment_id", type=int)
    prefill_alert_id = request.args.get("alert_id", type=int)
    prefill_title = ""
    prefill_desc = ""

    if prefill_alert_id:
        alert = db.session.get(FaultAlert, prefill_alert_id)
        if alert:
            prefill_equipment_id = alert.equipment_id
            prefill_title = f"Corrective Action: {alert.equipment.equipment_tag} {alert.sensor_type.title()} Alert"
            prefill_desc = f"Fault alert #{alert.id}: {alert.description}\nObserved {alert.observed_value} vs limit {alert.configured_limit}."

    if request.method == "POST":
        equip_id = request.form.get("equipment_id", type=int)
        alert_id = request.form.get("alert_id", type=int) or None
        title = request.form.get("title", "").strip()
        problem_description = request.form.get("problem_description", "").strip()
        priority = request.form.get("priority", WorkOrder.PRIORITY_MEDIUM)
        due_date_str = request.form.get("due_date")
        assigned_to_id = request.form.get("assigned_to_id", type=int) or None

        if not equip_id or not title or not problem_description:
            flash("Equipment, Title, and Problem Description are required.", "danger")
            return render_template(
                "maintenance/work_order_form.html",
                equipment_list=equipment_list,
                technicians=technicians,
                order=None,
                prefill_equip=prefill_equipment_id,
                prefill_alert=prefill_alert_id,
                prefill_title=prefill_title,
                prefill_desc=prefill_desc,
            )

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        wo = create_work_order(
            equipment_id=equip_id,
            title=title,
            problem_description=problem_description,
            priority=priority,
            created_by_id=user.id,
            alert_id=alert_id,
            due_date=due_date,
            assigned_to_id=assigned_to_id,
        )
        flash(f"Work Order '{wo.work_order_number}' created successfully.", "success")
        return redirect(url_for("maintenance.order_detail", order_id=wo.id))

    return render_template(
        "maintenance/work_order_form.html",
        equipment_list=equipment_list,
        technicians=technicians,
        order=None,
        prefill_equip=prefill_equipment_id,
        prefill_alert=prefill_alert_id,
        prefill_title=prefill_title,
        prefill_desc=prefill_desc,
    )


@maintenance_bp.route("/work-orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = WorkOrder.query.get_or_404(order_id)
    technicians = User.query.filter(User.role.in_([User.ROLE_TECHNICIAN, User.ROLE_ENGINEER]), User.is_active == True).all()
    return render_template(
        "maintenance/work_order_detail.html",
        order=order,
        technicians=technicians,
    )


@maintenance_bp.route("/work-orders/<int:order_id>/update", methods=["POST"])
@login_required
def update_order(order_id):
    user = get_current_user()
    status = request.form.get("status")
    priority = request.form.get("priority")
    assigned_to_id = request.form.get("assigned_to_id", type=int)
    due_date_str = request.form.get("due_date")
    findings = request.form.get("inspection_findings")
    actions = request.form.get("repair_actions")
    parts = request.form.get("parts_used")
    labor = request.form.get("labor_hours")
    cost = request.form.get("maintenance_cost")

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    update_work_order(
        work_order_id=order_id,
        user_id=user.id,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        due_date=due_date,
        inspection_findings=findings,
        repair_actions=actions,
        parts_used=parts,
        labor_hours=float(labor) if labor else None,
        maintenance_cost=float(cost) if cost else None,
    )
    flash("Work order progress updated.", "success")
    return redirect(url_for("maintenance.order_detail", order_id=order_id))


@maintenance_bp.route("/work-orders/<int:order_id>/complete", methods=["POST"])
@login_required
def complete_order(order_id):
    user = get_current_user()
    reason = request.form.get("completion_reason", "Maintenance work completed and verified.")
    findings = request.form.get("inspection_findings")
    actions = request.form.get("repair_actions")
    parts = request.form.get("parts_used")
    labor = float(request.form.get("labor_hours") or 0.0)
    cost = float(request.form.get("maintenance_cost") or 0.0)
    downtime = float(request.form.get("estimated_downtime_hours") or 0.0)
    resolve_alert_flag = request.form.get("resolve_alert") == "on"

    complete_work_order(
        work_order_id=order_id,
        user_id=user.id,
        completion_reason=reason,
        inspection_findings=findings,
        repair_actions=actions,
        parts_used=parts,
        labor_hours=labor,
        maintenance_cost=cost,
        estimated_downtime_hours=downtime,
        resolve_linked_alert=resolve_alert_flag,
    )
    flash("Work order marked as COMPLETED and added to equipment maintenance history.", "success")
    return redirect(url_for("maintenance.order_detail", order_id=order_id))


@maintenance_bp.route("/work-orders/<int:order_id>/cancel", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN, User.ROLE_ENGINEER)
def cancel_order(order_id):
    user = get_current_user()
    reason = request.form.get("cancel_reason", "Work order cancelled by maintenance coordinator.")
    cancel_work_order(work_order_id=order_id, user_id=user.id, reason=reason)
    flash("Work order cancelled.", "info")
    return redirect(url_for("maintenance.order_detail", order_id=order_id))


# ── Preventive Schedules ─────────────────────────────────────────────────────
@maintenance_bp.route("/maintenance/schedules")
@login_required
def schedules():
    equipment_id = request.args.get("equipment_id", type=int)
    query = MaintenanceSchedule.query
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)

    scheds = query.order_by(MaintenanceSchedule.next_due_date.asc()).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    technicians = User.query.filter(User.role.in_([User.ROLE_TECHNICIAN, User.ROLE_ENGINEER]), User.is_active == True).all()

    return render_template(
        "maintenance/schedules.html",
        schedules=scheds,
        equipment_list=equipment_list,
        technicians=technicians,
        today=date.today(),
        selected_equip=equipment_id,
    )


@maintenance_bp.route("/maintenance/schedules/new", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN, User.ROLE_ENGINEER)
def create_schedule():
    equip_id = request.form.get("equipment_id", type=int)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    interval_days = request.form.get("interval_days", 30, type=int)
    next_due_str = request.form.get("next_due_date")
    assigned_to_id = request.form.get("assigned_to_id", type=int) or None

    if not equip_id or not title or not next_due_str:
        flash("Equipment, Title, and Next Due Date are required.", "danger")
        return redirect(url_for("maintenance.schedules"))

    try:
        next_due = datetime.strptime(next_due_str, "%Y-%m-%d").date()
    except ValueError:
        next_due = date.today() + timedelta(days=interval_days)

    sched = MaintenanceSchedule(
        equipment_id=equip_id,
        title=title,
        description=description,
        interval_days=interval_days,
        next_due_date=next_due,
        assigned_to_id=assigned_to_id,
        is_active=True,
    )
    db.session.add(sched)
    db.session.commit()
    log_action("CREATE_SCHEDULE", "MaintenanceSchedule", sched.id, f"Created schedule '{title}'")
    flash("Preventive maintenance schedule created.", "success")
    return redirect(url_for("maintenance.schedules"))


@maintenance_bp.route("/maintenance/schedules/<int:sched_id>/execute", methods=["POST"])
@login_required
def execute_schedule_task(sched_id):
    user = get_current_user()
    notes = request.form.get("notes", "Routine scheduled check executed.")
    labor = float(request.form.get("labor_hours") or 1.0)
    cost = float(request.form.get("cost") or 0.0)

    complete_schedule(schedule_id=sched_id, user_id=user.id, notes=notes, labor_hours=labor, cost=cost)
    flash("Scheduled service completed. Next due date updated.", "success")
    return redirect(url_for("maintenance.schedules"))


# ── Maintenance History ──────────────────────────────────────────────────────
@maintenance_bp.route("/maintenance/history")
@login_required
def history():
    equipment_id = request.args.get("equipment_id", type=int)
    record_type = request.args.get("record_type", "")

    query = MaintenanceRecord.query
    if equipment_id:
        query = query.filter_by(equipment_id=equipment_id)
    if record_type:
        query = query.filter_by(record_type=record_type)

    records = query.order_by(MaintenanceRecord.performed_at.desc()).all()
    equipment_list = Equipment.query.filter_by(is_active=True).all()

    total_cost = sum(r.cost for r in records)
    total_hours = sum(r.labor_hours for r in records)
    total_downtime = sum(r.estimated_downtime_hours for r in records)

    return render_template(
        "maintenance/history.html",
        records=records,
        equipment_list=equipment_list,
        record_types=MaintenanceRecord.RECORD_TYPES,
        total_cost=round(total_cost, 2),
        total_hours=round(total_hours, 1),
        total_downtime=round(total_downtime, 1),
        selected_equip=equipment_id,
        selected_type=record_type,
    )
