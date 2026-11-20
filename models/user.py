from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = "users"

    ROLE_ADMIN = "administrator"
    ROLE_ENGINEER = "maintenance_engineer"
    ROLE_TECHNICIAN = "technician"
    ROLE_MANAGER = "plant_manager"

    ALL_ROLES = [ROLE_ADMIN, ROLE_ENGINEER, ROLE_TECHNICIAN, ROLE_MANAGER]

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(30), nullable=True)
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    sms_notifications = db.Column(db.Boolean, default=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=ROLE_TECHNICIAN)
    full_name = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    notifications = db.relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    @property
    def is_admin(self) -> bool:
        return self.role == self.ROLE_ADMIN

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone_number": self.phone_number,
            "email_notifications": self.email_notifications,
            "sms_notifications": self.sms_notifications,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
