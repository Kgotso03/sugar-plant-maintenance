"""
Alert management service for acknowledging, resolving, and investigating alerts.
"""
from datetime import datetime, timezone
from extensions import db
from models.alert import FaultAlert
from services.audit_service import log_action


def acknowledge_alert(alert_id: int, user_id: int, comment: str = None) -> FaultAlert:
    alert = FaultAlert.query.get_or_404(alert_id)
    alert.status = FaultAlert.STATUS_ACKNOWLEDGED
    alert.acknowledged_by_id = user_id
    alert.acknowledged_at = datetime.now(timezone.utc)
    if comment:
        alert.comments = (alert.comments or "") + f"\n[{alert.acknowledged_at.strftime('%Y-%m-%d %H:%M')}] ACK: {comment}"

    db.session.commit()
    log_action("ACKNOWLEDGE_ALERT", "FaultAlert", alert.id, f"Alert #{alert.id} acknowledged by user #{user_id}")
    return alert


def resolve_alert(alert_id: int, user_id: int, comment: str = None) -> FaultAlert:
    alert = FaultAlert.query.get_or_404(alert_id)
    alert.status = FaultAlert.STATUS_RESOLVED
    alert.resolved_by_id = user_id
    alert.resolved_at = datetime.now(timezone.utc)
    if comment:
        alert.comments = (alert.comments or "") + f"\n[{alert.resolved_at.strftime('%Y-%m-%d %H:%M')}] RESOLVED: {comment}"

    db.session.commit()
    log_action("RESOLVE_ALERT", "FaultAlert", alert.id, f"Alert #{alert.id} resolved by user #{user_id}")
    return alert


def add_comment(alert_id: int, user_id: int, comment: str) -> FaultAlert:
    alert = FaultAlert.query.get_or_404(alert_id)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    alert.comments = (alert.comments or "") + f"\n[{now_str}] Note: {comment}"
    db.session.commit()
    log_action("COMMENT_ALERT", "FaultAlert", alert.id, f"Note added on alert #{alert.id}")
    return alert
