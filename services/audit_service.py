"""
Audit logging service for tracking system actions and changes.
"""
from flask import request
from extensions import db
from models.audit import AuditLog
from services.auth_service import get_current_user


def log_action(action: str, entity_type: str, entity_id: int = None, details: str = None):
    """Safely records an audit log entry."""
    try:
        user = get_current_user()
        user_id = user.id if user else None
        ip_addr = request.remote_addr if request else "127.0.0.1"

        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_addr,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Logging failure should not crash main request
        print(f"Failed to record audit log: {e}")
