"""
Comprehensive Automated Test Suite for Sugar Plant Predictive Maintenance System.
Tests:
- Database connectivity
- User authentication & RBAC access permissions
- Equipment registration, editing, and retrieval
- Synthetic sensor reading storage
- Threshold breach evaluation & alert deduplication
- Alert acknowledgement, commenting, and resolution
- Simulation engine lifecycle (start, pause, resume, stop, single-step)
- Machine learning synthetic data generation, model training, and failure risk prediction
- Work order creation, status transitions, and completion
- Maintenance history recording
- Reports generation & CSV export
- Input validation and error handling
"""

import os
import pytest
from datetime import datetime, date, timezone
from app import create_app
from extensions import db
from models.user import User
from models.plant import PlantArea
from models.equipment import Equipment
from models.sensor import SensorDefinition, SensorReading
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from services.threshold_engine import ThresholdEngine
from services.simulator import simulator
from services.prediction_engine import PredictionEngine
from ml.train_model import train_and_save_model
from ml.synthetic_data import generate_synthetic_maintenance_dataset


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Create test users with different roles
        admin = User(username="test_admin", email="admin@test.local", role=User.ROLE_ADMIN)
        admin.set_password("AdminPass123!")
        engineer = User(username="test_eng", email="eng@test.local", role=User.ROLE_ENGINEER)
        engineer.set_password("EngPass123!")
        tech = User(username="test_tech", email="tech@test.local", role=User.ROLE_TECHNICIAN)
        tech.set_password("TechPass123!")
        manager = User(username="test_mgr", email="mgr@test.local", role=User.ROLE_MANAGER)
        manager.set_password("MgrPass123!")

        db.session.add_all([admin, engineer, tech, manager])

        # Create test plant area & equipment
        area = PlantArea(name="Test Milling Sector", code="TEST_MILL", description="Milling tandem")
        db.session.add(area)
        db.session.flush()

        equip = Equipment(
            equipment_tag="TST-101",
            name="Test Cane Shredder",
            equipment_type="Crusher",
            plant_area_id=area.id,
            operating_status=Equipment.STATUS_RUNNING,
        )
        db.session.add(equip)
        db.session.flush()

        # Add sensor definition with strict thresholds
        sensor = SensorDefinition(
            equipment_id=equip.id,
            sensor_type="temperature",
            sensor_name="Bearing Temperature",
            unit="C",
            min_acceptable=10.0,
            max_acceptable=90.0,
            warning_max=75.0,
            critical_max=85.0,
            is_enabled=True,
        )
        db.session.add(sensor)
        db.session.commit()

        simulator.init_app(app)

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── 1. Database Connectivity & Smoke Tests ──────────────────────────────────
def test_db_connectivity(app):
    with app.app_context():
        users = User.query.all()
        assert len(users) == 4
        equip = Equipment.query.filter_by(equipment_tag="TST-101").first()
        assert equip is not None
        assert equip.name == "Test Cane Shredder"


# ── 2. User Authentication & RBAC Tests ─────────────────────────────────────
def test_login_logout(client):
    # GET login page
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Sign In to Control Room" in res.data

    # POST valid login
    res = client.post("/login", data={"username": "test_admin", "password": "AdminPass123!"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Operations & Predictive Health Dashboard" in res.data

    # POST invalid login
    client.get("/logout")
    res = client.post("/login", data={"username": "test_admin", "password": "WrongPassword"}, follow_redirects=True)
    assert b"Invalid username or password" in res.data


def test_rbac_access_control(client):
    # Technician should not be allowed to access user management (Admin only)
    client.post("/login", data={"username": "test_tech", "password": "TechPass123!"}, follow_redirects=True)
    res = client.get("/users", follow_redirects=True)
    assert res.status_code == 200
    # Redirected to dashboard due to insufficient permissions
    assert b"Access denied: You do not have permission" in res.data

    # Admin CAN access user management
    client.get("/logout")
    client.post("/login", data={"username": "test_admin", "password": "AdminPass123!"}, follow_redirects=True)
    res = client.get("/users")
    assert res.status_code == 200
    assert b"User & Role Management" in res.data


# ── 3. Equipment Registration & Editing ──────────────────────────────────────
def test_equipment_lifecycle(client, app):
    client.post("/login", data={"username": "test_admin", "password": "AdminPass123!"})

    with app.app_context():
        area = PlantArea.query.first()
        area_id = area.id

    # Create new equipment
    res = client.post(
        "/equipment/new",
        data={
            "equipment_tag": "PMP-999",
            "name": "Slurry Feed Pump",
            "equipment_type": "Pump",
            "plant_area_id": area_id,
            "description": "High pressure centrifugal pump",
            "operating_status": "running",
            "installation_date": "2024-01-15",
            "maintenance_info": "Grease every 500 hours",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"PMP-999" in res.data

    with app.app_context():
        pmp = Equipment.query.filter_by(equipment_tag="PMP-999").first()
        assert pmp is not None
        assert len(pmp.sensors) >= 3  # Default sensors initialized automatically

    # Edit equipment
    res = client.post(
        f"/equipment/{pmp.id}/edit",
        data={
            "name": "Upgraded Slurry Feed Pump",
            "equipment_type": "Pump",
            "plant_area_id": area_id,
            "description": "Upgraded impeller",
            "operating_status": "idle",
            "maintenance_info": "Inspect monthly",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    with app.app_context():
        updated = db.session.get(Equipment, pmp.id)
        assert updated.name == "Upgraded Slurry Feed Pump"
        assert updated.operating_status == "idle"


# ── 4. Threshold Breach Detection & Alert Deduplication ──────────────────────
def test_threshold_evaluation_and_alerts(app):
    with app.app_context():
        equip = Equipment.query.filter_by(equipment_tag="TST-101").first()
        sensor = SensorDefinition.query.filter_by(equipment_id=equip.id, sensor_type="temperature").first()

        # Normal reading (60°C) -> status normal, no alert
        r1, a1 = ThresholdEngine.process_reading(equip, sensor, 60.0)
        assert r1.status == SensorReading.STATUS_NORMAL
        assert a1 is None

        # Warning reading (78°C) -> status warning, alert created
        r2, a2 = ThresholdEngine.process_reading(equip, sensor, 78.0)
        assert r2.status == SensorReading.STATUS_WARNING
        assert a2 is not None
        assert a2.severity == FaultAlert.SEVERITY_WARNING
        assert a2.status == FaultAlert.STATUS_ACTIVE
        first_alert_id = a2.id

        # Consecutive breach reading (80°C) -> deduplication applies, updates existing alert
        r3, a3 = ThresholdEngine.process_reading(equip, sensor, 80.0)
        assert r3.status == SensorReading.STATUS_WARNING
        assert a3.id == first_alert_id
        assert a3.observed_value == 80.0

        # Critical breach reading (95°C) -> escalates existing alert to CRITICAL
        r4, a4 = ThresholdEngine.process_reading(equip, sensor, 95.0)
        assert r4.status == SensorReading.STATUS_CRITICAL
        assert a4.id == first_alert_id
        assert a4.severity == FaultAlert.SEVERITY_CRITICAL


# ── 5. Alert Acknowledgement & Resolution ────────────────────────────────────
def test_alert_ack_and_resolve(client, app):
    with app.app_context():
        equip = Equipment.query.filter_by(equipment_tag="TST-101").first()
        sensor = SensorDefinition.query.first()
        _, alert = ThresholdEngine.process_reading(equip, sensor, 88.0)
        db.session.commit()
        alert_id = alert.id

    client.post("/login", data={"username": "test_eng", "password": "EngPass123!"})

    # Acknowledge
    res = client.post(f"/alerts/{alert_id}/acknowledge", data={"comment": "Investigating on site"}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        a = db.session.get(FaultAlert, alert_id)
        assert a.status == FaultAlert.STATUS_ACKNOWLEDGED
        assert "Investigating on site" in a.comments

    # Resolve
    res = client.post(f"/alerts/{alert_id}/resolve", data={"comment": "Lube restored; temp normal"}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        a = db.session.get(FaultAlert, alert_id)
        assert a.status == FaultAlert.STATUS_RESOLVED


# ── 6. Simulation Engine Lifecycle ───────────────────────────────────────────
def test_simulation_lifecycle(app):
    with app.app_context():
        # Start simulation in single-step / discrete mode
        simulator.start(scenario="high_temperature", speed_factor=2.0)
        st = simulator.get_status()
        assert st["is_running"] is True
        assert st["scenario"] == "high_temperature"

        # Execute single tick
        readings = simulator.execute_step_once()
        assert len(readings) > 0

        # Pause & Resume
        simulator.pause()
        assert simulator.get_status()["is_paused"] is True
        simulator.resume()
        assert simulator.get_status()["is_paused"] is False

        # Stop
        simulator.stop()
        assert simulator.get_status()["is_running"] is False


# ── 7. Machine Learning Dataset, Training & Prediction ───────────────────────
def test_ml_pipeline(app):
    with app.app_context():
        # Synthetic data generation
        df = generate_synthetic_maintenance_dataset(n_samples=200, random_state=42)
        assert len(df) == 200
        assert "temperature" in df.columns
        assert "risk_label" in df.columns

        # Train & evaluate model
        model, metrics = train_and_save_model(n_samples=300, random_state=42)
        assert metrics["overall_accuracy"] > 0.85
        assert len(metrics["confusion_matrix"]) == 3

        # Run prediction on equipment
        equip = Equipment.query.filter_by(equipment_tag="TST-101").first()
        pred = PredictionEngine.predict_equipment(equip, persist=True)
        assert pred is not None
        assert pred.risk_category in ("low", "medium", "high")
        assert 0.0 <= pred.risk_score <= 1.0
        assert len(pred.get_factors()) > 0


# ── 8. Work Order & Maintenance History ──────────────────────────────────────
def test_work_order_workflow(client, app):
    client.post("/login", data={"username": "test_eng", "password": "EngPass123!"})

    with app.app_context():
        equip = Equipment.query.filter_by(equipment_tag="TST-101").first()
        tech = User.query.filter_by(role=User.ROLE_TECHNICIAN).first()
        eq_id = equip.id
        tech_id = tech.id

    # Create Work Order
    res = client.post(
        "/work-orders/new",
        data={
            "equipment_id": eq_id,
            "title": "Replace Motor Drive End Bearing",
            "problem_description": "Vibration levels rising toward warning threshold",
            "priority": "high",
            "assigned_to_id": tech_id,
            "due_date": "2026-11-15",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Replace Motor Drive End Bearing" in res.data

    with app.app_context():
        wo = WorkOrder.query.filter_by(title="Replace Motor Drive End Bearing").first()
        assert wo is not None
        wo_id = wo.id

    # Update progress
    client.post(
        f"/work-orders/{wo_id}/update",
        data={
            "status": "in_progress",
            "inspection_findings": "Bearing cage worn",
            "repair_actions": "Pressing out old race",
            "labor_hours": "2.5",
            "maintenance_cost": "210.00",
        },
        follow_redirects=True,
    )

    with app.app_context():
        wo_updated = db.session.get(WorkOrder, wo_id)
        assert wo_updated.status == "in_progress"
        assert wo_updated.labor_hours == 2.5

    # Complete Work Order
    client.post(
        f"/work-orders/{wo_id}/complete",
        data={
            "completion_reason": "New SKF bearing installed and test run at 1450 RPM clean",
            "labor_hours": "4.0",
            "maintenance_cost": "350.00",
            "estimated_downtime_hours": "2.0",
        },
        follow_redirects=True,
    )

    with app.app_context():
        wo_completed = db.session.get(WorkOrder, wo_id)
        assert wo_completed.status == WorkOrder.STATUS_COMPLETED

        # Check maintenance history was automatically recorded
        mrec = MaintenanceRecord.query.filter_by(work_order_id=wo_id).first()
        assert mrec is not None
        assert mrec.cost == 350.00
        assert mrec.estimated_downtime_hours == 2.0


# ── 9. Reports & CSV Export ──────────────────────────────────────────────────
def test_reports_and_csv_export(client):
    client.post("/login", data={"username": "test_mgr", "password": "MgrPass123!"})

    # Equipment report HTML
    res = client.get("/reports?report_type=equipment_condition")
    assert res.status_code == 200
    assert b"Equipment Condition" in res.data

    # CSV Export
    csv_res = client.get("/reports/export-csv?report_type=equipment_condition")
    assert csv_res.status_code == 200
    assert csv_res.headers["Content-Type"].startswith("text/csv")
    assert b"Tag" in csv_res.data
    assert b"TST-101" in csv_res.data

    # Print view
    print_res = client.get("/reports/print")
    assert print_res.status_code == 200
    assert b"Sugar Refinery Plant Maintenance Audit Report" in print_res.data

