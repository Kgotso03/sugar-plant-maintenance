from datetime import datetime, timezone
from extensions import db


class PlantArea(db.Model):
    __tablename__ = "plant_areas"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    equipment = db.relationship("Equipment", back_populates="plant_area", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "equipment_count": len(self.equipment) if self.equipment else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
