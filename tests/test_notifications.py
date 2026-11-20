"""
Automated Test Suite for Notifications: Email, SMS, Work Order alerts, Fault warnings, and Credentials.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.plant import PlantArea
from models.equipment import Equipment
from models.alert import FaultAlert
from models.maintenance import WorkOrder, MaintenanceSchedule
from models.notification import NotificationLog
from services.notification_service import notification_service
from datetime import date


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        admin = User(
            username="admin_user",
            email="admin@sugarplant.local",
            phone_number="+27820000001",
            role=User.ROLE_ADMIN,
            email_notifications=True,
            sms_notifications=True,
        )
        admin.set_password("AdminPass123!")

        tech = User(
            username="tech_john",
            email="john@sugarplant.local",
            phone_number="+27820000002",
            role=User.ROLE_TECHNICIAN,
            email_notifications=True,
            sms_notifications=True,
        )
        tech.set_password("TechPass123!")

        db.session.add_all([admin, tech])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_notification_dispatch_both_channels(app):
    with app.app_context():
        user = User.query.filter_by(username="tech_john").first()
        logs = notification_service.dispatch_notification(
            user=user,
            title="Safety Alert",
            message="Check boiler pressure.",
            category=NotificationLog.CATEGORY_FAULT_ALERT,
        )
        assert len(logs) == 2
        channels = [l.channel for l in logs]
        assert NotificationLog.CHANNEL_EMAIL in channels
        assert NotificationLog.CHANNEL_SMS in channels
        assert all(l.status == NotificationLog.STATUS_SENT for l in logs)


def test_notification_respects_user_preferences(app):
    with app.app_context():
        user = User.query.filter_by(username="tech_john").first()
        user.sms_notifications = False
        db.session.commit()

        logs = notification_service.dispatch_notification(
            user=user,
            title="Work Order Update",
            message="Status changed.",
            category=NotificationLog.CATEGORY_WORK_ORDER,
        )
        assert len(logs) == 1
        assert logs[0].channel == NotificationLog.CHANNEL_EMAIL


def test_user_credentials_notification(app):
    with app.app_context():
        user = User.query.filter_by(username="tech_john").first()
        logs = notification_service.notify_user_account_created(
            user=user,
            plain_password="TemporaryPassword123!",
            login_url="https://maintenance-y2ru.vercel.app/login",
        )
        assert len(logs) >= 1
        assert any(l.category == NotificationLog.CATEGORY_ACCOUNT for l in logs)
        assert any("TemporaryPassword123!" in l.message for l in logs)


def test_work_order_notification(app):
    with app.app_context():
        admin = User.query.filter_by(username="admin_user").first()
        tech = User.query.filter_by(username="tech_john").first()
        area = PlantArea(name="Milling", code="MILL")
        db.session.add(area)
        db.session.flush()

        equip = Equipment(name="Cane Crusher A", equipment_tag="CRUSH-01", plant_area_id=area.id, equipment_type="Crusher")
        db.session.add(equip)
        db.session.flush()

        wo = WorkOrder(
            work_order_number="WO-2026-TEST",
            equipment_id=equip.id,
            title="Bearing Replacement",
            problem_description="Excessive vibration reported",
            priority=WorkOrder.PRIORITY_HIGH,
            status=WorkOrder.STATUS_ASSIGNED,
            assigned_to_id=tech.id,
            created_by_id=admin.id,
        )
        db.session.add(wo)
        db.session.commit()

        logs = notification_service.notify_work_order_assigned(wo)
        assert len(logs) >= 1
        assert any(l.category == NotificationLog.CATEGORY_WORK_ORDER for l in logs)
        assert any("WO-2026-TEST" in l.title for l in logs)


def test_notifications_ui_and_unread_api(client, app):
    # Log in as tech
    with client.session_transaction() as sess:
        with app.app_context():
            tech = User.query.filter_by(username="tech_john").first()
            sess["user_id"] = tech.id
            sess["role"] = tech.role

    # Send a notification to tech
    with app.app_context():
        tech = User.query.filter_by(username="tech_john").first()
        notification_service.dispatch_notification(tech, "Test Bell", "Hello!")

    # Check unread count API
    res = client.get("/api/notifications/unread-count")
    assert res.status_code == 200
    data = res.get_json()
    assert data["unread_count"] >= 1

    # Mark all read
    res = client.post("/notifications/read-all", follow_redirects=True)
    assert res.status_code == 200

    # Verify unread is now 0
    res = client.get("/api/notifications/unread-count")
    assert res.get_json()["unread_count"] == 0
