"""
Clean Demo Data and Reset System for Live Performance.
Keeps only the system administrator account (`admin`) and foundational plant structure.
Removes:
  - All demo users (engineer, tech1, manager)
  - All simulated sensor telemetry records
  - All simulated fault alerts
  - All simulated ML failure predictions
  - All simulation run logs
  - All sample demo work orders and repair history records
"""

import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from extensions import db
from models.user import User
from models.sensor import SensorReading
from models.alert import FaultAlert
from models.prediction import FailurePrediction
from models.simulation import SimulationRun
from models.maintenance import WorkOrder, MaintenanceRecord, MaintenanceSchedule
from models.audit import AuditLog


def clean_demo_data(app=None):
    if app is None:
        app = create_app()

    with app.app_context():
        print("Cleaning demo data and preparing system for live performance...")

        # 1. Verify or create admin user
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin_pass = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin123!")
            admin = User(
                username="admin",
                email="admin@sugarplant.local",
                role=User.ROLE_ADMIN,
                full_name="System Administrator",
                is_active=True,
            )
            admin.set_password(admin_pass)
            db.session.add(admin)
            db.session.flush()
            print("  Created default admin user.")
        else:
            admin.is_active = True
            admin.role = User.ROLE_ADMIN
            db.session.flush()
            print("  Verified system admin user.")

        # 2. Delete maintenance records (history)
        num_mrec = MaintenanceRecord.query.delete()
        print(f"  Removed {num_mrec} demo maintenance records.")

        # 3. Delete work orders
        num_wo = WorkOrder.query.delete()
        print(f"  Removed {num_wo} demo work orders.")

        # 4. Reassign maintenance schedules to admin
        schedules = MaintenanceSchedule.query.all()
        for s in schedules:
            s.assigned_to_id = admin.id
        print(f"  Reassigned {len(schedules)} maintenance schedule templates to System Administrator.")

        # 5. Delete fault alerts
        num_alerts = FaultAlert.query.delete()
        print(f"  Removed {num_alerts} demo fault alerts.")

        # 6. Delete sensor telemetry readings
        num_readings = SensorReading.query.delete()
        print(f"  Removed {num_readings} demo sensor readings.")

        # 7. Delete ML failure predictions
        num_preds = FailurePrediction.query.delete()
        print(f"  Removed {num_preds} demo failure predictions.")

        # 8. Delete simulation run history
        num_runs = SimulationRun.query.delete()
        print(f"  Removed {num_runs} demo simulation run records.")

        # 9. Clean audit logs not associated with admin
        num_audit = AuditLog.query.filter(AuditLog.user_id != admin.id).delete()
        print(f"  Removed {num_audit} demo user audit log entries.")

        # 10. Delete non-admin demo users
        demo_users = User.query.filter(User.username != "admin").all()
        for u in demo_users:
            print(f"  Deleting demo account: {u.username} ({u.role})")
            db.session.delete(u)

        # Record cleanup in audit log
        cleanup_log = AuditLog(
            user_id=admin.id,
            action="CLEAN_DEMO_DATA",
            entity_type="SYSTEM",
            entity_id=None,
            details="Cleared all demo accounts (except admin) and wiped all simulated operational records for live performance.",
            ip_address="127.0.0.1",
        )
        db.session.add(cleanup_log)

        db.session.commit()
        print("\nAll demo data and demo accounts successfully removed!")
        print("System is clean and ready for live performance monitoring and training.")


if __name__ == "__main__":
    clean_demo_data()

