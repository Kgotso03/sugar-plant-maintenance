"""
System Settings, Safety Disclaimers, and Audit Log Explorer.
"""
from flask import Blueprint, render_template, request, flash
from extensions import db
from models.audit import AuditLog
from models.user import User
from services.auth_service import login_required, roles_required
from services.simulator import simulator

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
@login_required
def index():
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    sim_status = simulator.get_status()

    return render_template(
        "settings/index.html",
        audit_logs=audit_logs,
        sim_status=sim_status,
    )
