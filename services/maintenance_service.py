"""
Maintenance Management Service.
Handles work order lifecycles, preventive schedules, and historical maintenance logs.
"""
from datetime import datetime, date, timedelta, timezone
from extensions import db
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from models.alert import FaultAlert
from models.equipment import Equipment
from services.audit_service import log_action
from services.notification_service import notification_service


def generate_work_order_number() -> str:
    """Generates sequential work order identifier (e.g. WO-2026-0002)."""
    current_year = datetime.now(timezone.utc).year
    prefix = f"WO-{current_year}-"
    last_wo = (
        WorkOrder.query.filter(WorkOrder.work_order_number.like(f"{prefix}%"))
        .order_by(WorkOrder.id.desc())
        .first()
    )
    if last_wo:
        try:
            seq = int(last_wo.work_order_number.split("-")[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_work_order(
    equipment_id: int,
    title: str,
    problem_description: str,
    priority: str,
    created_by_id: int,
    alert_id: int = None,
    due_date: date = None,
    assigned_to_id: int = None,
) -> WorkOrder:
    wo_num = generate_work_order_number()
    status = WorkOrder.STATUS_ASSIGNED if assigned_to_id else WorkOrder.STATUS_OPEN

    wo = WorkOrder(
        work_order_number=wo_num,
        equipment_id=equipment_id,
        alert_id=alert_id,
        title=title,
        problem_description=problem_description,
        priority=priority,
        status=status,
        due_date=due_date,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
    )
    db.session.add(wo)
    db.session.commit()

    # Dispatch notification to assigned technician
    if assigned_to_id:
        try:
            notification_service.notify_work_order_assigned(wo)
        except Exception as e:
            print(f"[NOTIFICATION ERROR] {e}")

    log_action("CREATE_WORK_ORDER", "WorkOrder", wo.id, f"Created Work Order {wo.work_order_number}")
    return wo


def update_work_order(
    work_order_id: int,
    user_id: int,
    status: str = None,
    priority: str = None,
    assigned_to_id: int = None,
    due_date: date = None,
    inspection_findings: str = None,
    repair_actions: str = None,
    parts_used: str = None,
    labor_hours: float = None,
    maintenance_cost: float = None,
) -> WorkOrder:
    wo = WorkOrder.query.get_or_404(work_order_id)
    old_status = wo.status
    old_assigned_to_id = wo.assigned_to_id

    if status and status in WorkOrder.STATUSES:
        wo.status = status
    if priority and priority in WorkOrder.PRIORITIES:
        wo.priority = priority
    if assigned_to_id is not None:
        wo.assigned_to_id = assigned_to_id if assigned_to_id > 0 else None
    if due_date is not None:
        wo.due_date = due_date
    if inspection_findings is not None:
        wo.inspection_findings = inspection_findings
    if repair_actions is not None:
        wo.repair_actions = repair_actions
    if parts_used is not None:
        wo.parts_used = parts_used
    if labor_hours is not None:
        wo.labor_hours = float(labor_hours)
    if maintenance_cost is not None:
        wo.maintenance_cost = float(maintenance_cost)

    db.session.commit()

    # Dispatch notification if assignment changed
    if assigned_to_id is not None and assigned_to_id > 0 and assigned_to_id != old_assigned_to_id:
        try:
            notification_service.notify_work_order_assigned(wo)
        except Exception as e:
            print(f"[NOTIFICATION ERROR] {e}")

    # Dispatch notification if status changed
    if status and status != old_status:
        try:
            notification_service.notify_work_order_status(wo, old_status, wo.status)
        except Exception as e:
            print(f"[NOTIFICATION ERROR] {e}")

    log_action("UPDATE_WORK_ORDER", "WorkOrder", wo.id, f"Updated Work Order {wo.work_order_number}")
    return wo


def complete_work_order(
    work_order_id: int,
    user_id: int,
    completion_reason: str,
    inspection_findings: str = None,
    repair_actions: str = None,
    parts_used: str = None,
    labor_hours: float = 0.0,
    maintenance_cost: float = 0.0,
    estimated_downtime_hours: float = 0.0,
    resolve_linked_alert: bool = True,
) -> WorkOrder:
    wo = WorkOrder.query.get_or_404(work_order_id)
    old_status = wo.status
    now = datetime.now(timezone.utc)

    wo.status = WorkOrder.STATUS_COMPLETED
    wo.completed_at = now
    wo.completion_reason = completion_reason
    if inspection_findings:
        wo.inspection_findings = inspection_findings
    if repair_actions:
        wo.repair_actions = repair_actions
    if parts_used:
        wo.parts_used = parts_used
    if labor_hours:
        wo.labor_hours = float(labor_hours)
    if maintenance_cost:
        wo.maintenance_cost = float(maintenance_cost)

    # Persist permanent maintenance history record
    mrec = MaintenanceRecord(
        equipment_id=wo.equipment_id,
        work_order_id=wo.id,
        record_type=MaintenanceRecord.TYPE_CORRECTIVE if wo.alert_id else MaintenanceRecord.TYPE_PREVENTIVE,
        title=f"Completed {wo.work_order_number}: {wo.title}",
        description=wo.problem_description,
        action_taken=wo.repair_actions or completion_reason,
        parts_replaced=wo.parts_used,
        labor_hours=wo.labor_hours,
        cost=wo.maintenance_cost,
        estimated_downtime_hours=float(estimated_downtime_hours),
        performed_by_id=wo.assigned_to_id or user_id,
        performed_at=now,
    )
    db.session.add(mrec)

    # Resolve linked alert if requested
    if resolve_linked_alert and wo.alert_id:
        alert = db.session.get(FaultAlert, wo.alert_id)
        if alert and alert.status != FaultAlert.STATUS_RESOLVED:
            alert.status = FaultAlert.STATUS_RESOLVED
            alert.resolved_by_id = user_id
            alert.resolved_at = now
            alert.comments = (alert.comments or "") + f"\nResolved via completed Work Order {wo.work_order_number}."

    db.session.commit()

    # Dispatch notification on completion
    try:
        notification_service.notify_work_order_status(wo, old_status, WorkOrder.STATUS_COMPLETED)
    except Exception as e:
        print(f"[NOTIFICATION ERROR] {e}")

    log_action("COMPLETE_WORK_ORDER", "WorkOrder", wo.id, f"Completed Work Order {wo.work_order_number}")
    return wo


def cancel_work_order(work_order_id: int, user_id: int, reason: str) -> WorkOrder:
    wo = WorkOrder.query.get_or_404(work_order_id)
    wo.status = WorkOrder.STATUS_CANCELLED
    wo.completion_reason = f"Cancelled: {reason}"
    db.session.commit()
    log_action("CANCEL_WORK_ORDER", "WorkOrder", wo.id, f"Cancelled Work Order {wo.work_order_number}")
    return wo


def complete_schedule(schedule_id: int, user_id: int, notes: str, labor_hours: float = 1.0, cost: float = 0.0):
    """Marks a preventive schedule task complete and rolls date forward."""
    sched = MaintenanceSchedule.query.get_or_404(schedule_id)
    now = datetime.now(timezone.utc)

    sched.last_performed_at = now
    sched.next_due_date = date.today() + timedelta(days=sched.interval_days)

    mrec = MaintenanceRecord(
        equipment_id=sched.equipment_id,
        work_order_id=None,
        record_type=MaintenanceRecord.TYPE_PREVENTIVE,
        title=f"Preventive: {sched.title}",
        description=sched.description or "Routine preventive maintenance schedule executed.",
        action_taken=notes or "Service and calibration completed as scheduled.",
        labor_hours=float(labor_hours),
        cost=float(cost),
        estimated_downtime_hours=0.5,
        performed_by_id=user_id,
        performed_at=now,
    )
    db.session.add(mrec)
    db.session.commit()

    log_action("COMPLETE_SCHEDULE", "MaintenanceSchedule", sched.id, f"Executed preventive schedule '{sched.title}'")
    return sched
