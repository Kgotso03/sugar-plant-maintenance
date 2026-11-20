from datetime import datetime, timezone
from extensions import db


class WorkOrder(db.Model):
    __tablename__ = "work_orders"

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CRITICAL = "critical"

    STATUS_OPEN = "open"
    STATUS_ASSIGNED = "assigned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_AWAITING_PARTS = "awaiting_parts"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    PRIORITIES = [PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
    STATUSES = [
        STATUS_OPEN,
        STATUS_ASSIGNED,
        STATUS_IN_PROGRESS,
        STATUS_AWAITING_PARTS,
        STATUS_COMPLETED,
        STATUS_CANCELLED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    work_order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("fault_alerts.id"), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    problem_description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default=PRIORITY_MEDIUM, nullable=False)
    status = db.Column(db.String(30), default=STATUS_OPEN, nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    inspection_findings = db.Column(db.Text, nullable=True)
    repair_actions = db.Column(db.Text, nullable=True)
    parts_used = db.Column(db.Text, nullable=True)
    labor_hours = db.Column(db.Float, default=0.0, nullable=False)
    maintenance_cost = db.Column(db.Float, default=0.0, nullable=False)
    completion_reason = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    equipment = db.relationship("Equipment", back_populates="work_orders")
    alert = db.relationship("FaultAlert", back_populates="work_orders")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    maintenance_record = db.relationship("MaintenanceRecord", back_populates="work_order", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_number": self.work_order_number,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "plant_area": self.equipment.plant_area.name if self.equipment and self.equipment.plant_area else None,
            "alert_id": self.alert_id,
            "title": self.title,
            "problem_description": self.problem_description,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assigned_to": self.assigned_to.full_name or self.assigned_to.username if self.assigned_to else "Unassigned",
            "assigned_to_id": self.assigned_to_id,
            "created_by": self.created_by.username if self.created_by else None,
            "inspection_findings": self.inspection_findings,
            "repair_actions": self.repair_actions,
            "parts_used": self.parts_used,
            "labor_hours": self.labor_hours,
            "maintenance_cost": self.maintenance_cost,
            "completion_reason": self.completion_reason,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MaintenanceRecord(db.Model):
    __tablename__ = "maintenance_records"

    TYPE_CORRECTIVE = "corrective"
    TYPE_PREVENTIVE = "preventive"
    TYPE_INSPECTION = "inspection"
    TYPE_EMERGENCY = "emergency"

    RECORD_TYPES = [TYPE_CORRECTIVE, TYPE_PREVENTIVE, TYPE_INSPECTION, TYPE_EMERGENCY]

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("work_orders.id"), nullable=True, index=True)
    record_type = db.Column(db.String(50), default=TYPE_CORRECTIVE, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text, nullable=False)
    parts_replaced = db.Column(db.Text, nullable=True)
    labor_hours = db.Column(db.Float, default=0.0, nullable=False)
    cost = db.Column(db.Float, default=0.0, nullable=False)
    estimated_downtime_hours = db.Column(db.Float, default=0.0, nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    performed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    equipment = db.relationship("Equipment", back_populates="maintenance_records")
    work_order = db.relationship("WorkOrder", back_populates="maintenance_record")
    performed_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "work_order_id": self.work_order_id,
            "work_order_number": self.work_order.work_order_number if self.work_order else None,
            "record_type": self.record_type,
            "title": self.title,
            "description": self.description,
            "action_taken": self.action_taken,
            "parts_replaced": self.parts_replaced,
            "labor_hours": self.labor_hours,
            "cost": self.cost,
            "estimated_downtime_hours": self.estimated_downtime_hours,
            "performed_by": self.performed_by.username if self.performed_by else None,
            "performed_at": self.performed_at.isoformat() if self.performed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MaintenanceSchedule(db.Model):
    __tablename__ = "maintenance_schedules"

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipment.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    interval_days = db.Column(db.Integer, nullable=False)
    last_performed_at = db.Column(db.DateTime, nullable=True)
    next_due_date = db.Column(db.Date, nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    equipment = db.relationship("Equipment", back_populates="schedules")
    assigned_to = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "equipment_tag": self.equipment.equipment_tag if self.equipment else None,
            "equipment_name": self.equipment.name if self.equipment else None,
            "title": self.title,
            "description": self.description,
            "interval_days": self.interval_days,
            "last_performed_at": self.last_performed_at.isoformat() if self.last_performed_at else None,
            "next_due_date": self.next_due_date.isoformat() if self.next_due_date else None,
            "assigned_to": self.assigned_to.full_name or self.assigned_to.username if self.assigned_to else "Unassigned",
            "assigned_to_id": self.assigned_to_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
