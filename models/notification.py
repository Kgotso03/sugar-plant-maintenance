"""
NotificationLog Model for tracking Email, SMS, and in-app industrial alerts.
"""
from datetime import datetime, timezone
from extensions import db


class NotificationLog(db.Model):
    __tablename__ = "notification_logs"

    CHANNEL_EMAIL = "email"
    CHANNEL_SMS = "sms"
    CHANNELS = [CHANNEL_EMAIL, CHANNEL_SMS]

    CATEGORY_ACCOUNT = "account"
    CATEGORY_WORK_ORDER = "work_order"
    CATEGORY_PM_SCHEDULE = "pm_schedule"
    CATEGORY_FAULT_ALERT = "fault_alert"
    CATEGORY_SYSTEM = "system"
    CATEGORIES = [CATEGORY_ACCOUNT, CATEGORY_WORK_ORDER, CATEGORY_PM_SCHEDULE, CATEGORY_FAULT_ALERT, CATEGORY_SYSTEM]

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SIMULATED = "simulated"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_email = db.Column(db.String(120), nullable=True)
    recipient_phone = db.Column(db.String(30), nullable=True)
    channel = db.Column(db.String(20), nullable=False, default=CHANNEL_EMAIL)
    category = db.Column(db.String(50), nullable=False, default=CATEGORY_SYSTEM)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SENT)
    error_message = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "recipient_email": self.recipient_email,
            "recipient_phone": self.recipient_phone,
            "channel": self.channel,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "status": self.status,
            "error_message": self.error_message,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
