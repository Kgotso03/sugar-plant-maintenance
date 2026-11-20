"""
Database seeding script for Sugar Plant Predictive Maintenance System.
Initializes all tables, sample plant areas, equipment, sensors, users,
and baseline maintenance schedules.
"""
import os
import sys
from datetime import datetime, date, timedelta, timezone

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from extensions import db
from models.user import User
from models.plant import PlantArea
from models.equipment import Equipment
from models.sensor import SensorDefinition
from models.maintenance import MaintenanceSchedule, WorkOrder, MaintenanceRecord
from models.audit import AuditLog


def seed_database(app=None):
    if app is None:
        app = create_app()

    with app.app_context():
        # Create all tables defined in models
        db.create_all()
        print("Database tables created / verified.")

        # ── 1. Users ────────────────────────────────────────────────────────
        admin_pass = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin123!")
        users_data = [
            {
                "username": "admin",
                "email": "admin@sugarplant.local",
                "role": User.ROLE_ADMIN,
                "full_name": "System Administrator",
                "password": admin_pass,
            },
        ]

        user_map = {}
        for udata in users_data:
            existing = User.query.filter_by(username=udata["username"]).first()
            if not existing:
                u = User(
                    username=udata["username"],
                    email=udata["email"],
                    role=udata["role"],
                    full_name=udata["full_name"],
                    is_active=True,
                )
                u.set_password(udata["password"])
                db.session.add(u)
                db.session.flush()
                user_map[udata["username"]] = u
                print(f"Created user: {u.username} ({u.role})")
            else:
                user_map[udata["username"]] = existing

        db.session.commit()

        # ── 2. Plant Areas ──────────────────────────────────────────────────
        plant_areas_data = [
            ("Cane handling and conveyor systems", "CANE_HANDLING", "Unloading, feeding, and carrier conveyors transporting harvested sugar cane."),
            ("Cane preparation", "CANE_PREP", "Heavy-duty knives, shredders, and fiberizers preparing cane for juice extraction."),
            ("Milling", "MILLING", "Multi-tandem roller mills extracting raw cane juice under high hydraulic pressure."),
            ("Boiler and steam systems", "BOILER_STEAM", "High-pressure bagasse-fired boilers producing process steam and cogeneration electricity."),
            ("Juice clarification", "JUICE_CLARIFICATION", "Liming, heating, and clarification tanks separating non-sugar impurities."),
            ("Evaporation", "EVAPORATION", "Multiple-effect evaporators concentrating clarified juice into syrup."),
            ("Sugar crystallisation", "CRYSTALLISATION", "Vacuum pans boiling syrup to initiate and grow sucrose sugar crystals."),
            ("Centrifugals", "CENTRIFUGALS", "High-speed centrifugal baskets separating crystal sugar from mother liquor molasses."),
            ("Packaging and material handling", "PACKAGING", "Conditioning, bulk silos, automated bagging, and dispatch conveyor lines."),
        ]

        area_map = {}
        for name, code, desc in plant_areas_data:
            area = PlantArea.query.filter_by(code=code).first()
            if not area:
                area = PlantArea(name=name, code=code, description=desc, is_active=True)
                db.session.add(area)
                db.session.flush()
                print(f"Created plant area: {name}")
            area_map[code] = area

        db.session.commit()

        # ── 3. Equipment ────────────────────────────────────────────────────
        equipment_data = [
            # Cane handling
            {
                "tag": "CV-101",
                "name": "Main Cane Feeder Conveyor",
                "type": "Conveyor Belt",
                "area": "CANE_HANDLING",
                "desc": "Heavy-duty 1800mm apron cane feeder belt with dual hydraulic drive.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("belt_speed", "Belt Linear Speed", "m/s", 0.0, 3.5, 0.5, 2.8, 0.2, 3.2),
                    ("motor_current", "Drive Motor Current", "A", 0.0, 150.0, 40.0, 120.0, 20.0, 140.0),
                    ("temperature", "Head Pulley Bearing Temp", "°C", 10.0, 95.0, 30.0, 75.0, 20.0, 85.0),
                    ("vibration", "Drive Gearbox Vibration", "mm/s", 0.0, 15.0, 1.0, 5.0, 0.5, 8.0),
                ],
            },
            {
                "tag": "CV-102",
                "name": "Bagasse Transfer Conveyor",
                "type": "Conveyor Belt",
                "area": "CANE_HANDLING",
                "desc": "High-inclination flight conveyor delivering fuel bagasse to boiler feed bins.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("belt_speed", "Bagasse Conveyor Speed", "m/s", 0.0, 4.0, 0.8, 3.2, 0.4, 3.8),
                    ("motor_current", "Drive Motor Current", "A", 0.0, 100.0, 25.0, 80.0, 15.0, 92.0),
                    ("vibration", "Tail Pulley Bearing Vibration", "mm/s", 0.0, 12.0, 0.8, 4.5, 0.3, 7.5),
                ],
            },
            # Cane prep
            {
                "tag": "CRU-201",
                "name": "Heavy Duty Cane Shredder / Fiberizer",
                "type": "Crusher",
                "area": "CANE_PREP",
                "desc": "High-inertia 72-hammer cane disintegrator with replaceable tungsten-carbide tips.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("motor_speed", "Rotor Shaft RPM", "RPM", 0.0, 1400.0, 900.0, 1150.0, 800.0, 1250.0),
                    ("vibration", "Rotor Bearing RMS Vibration", "mm/s", 0.0, 20.0, 1.5, 6.5, 0.8, 10.0),
                    ("temperature", "Main Bearing Temp", "°C", 15.0, 105.0, 35.0, 80.0, 25.0, 92.0),
                    ("motor_current", "500kW Motor Current", "A", 0.0, 600.0, 180.0, 520.0, 100.0, 570.0),
                ],
            },
            {
                "tag": "MTR-201",
                "name": "Cane Shredder Main Drive Motor",
                "type": "Electric Motor",
                "area": "CANE_PREP",
                "desc": "550kW 3.3kV slip-ring induction motor driving cane preparation shredder.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("motor_current", "Stator Current Phase A", "A", 0.0, 250.0, 60.0, 210.0, 30.0, 235.0),
                    ("temperature", "Stator Winding Temp", "°C", 20.0, 130.0, 45.0, 105.0, 30.0, 120.0),
                    ("motor_speed", "Motor Synchronous Speed", "RPM", 0.0, 1600.0, 1420.0, 1510.0, 1380.0, 1550.0),
                    ("vibration", "Drive-End Bearing Vibration", "mm/s", 0.0, 10.0, 0.5, 4.0, 0.2, 6.5),
                ],
            },
            # Milling
            {
                "tag": "GBX-301",
                "name": "Mill Tandem #1 Planetary Gearbox",
                "type": "Gearbox",
                "area": "MILLING",
                "desc": "Triple-reduction planetary speed reducer transmitting torque to Mill #1 top roller.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("temperature", "Lube Oil Sump Temp", "°C", 20.0, 90.0, 40.0, 72.0, 30.0, 82.0),
                    ("pressure", "Lube Oil Header Pressure", "bar", 0.0, 10.0, 2.5, 6.5, 1.8, 8.0),
                    ("vibration", "Input Pinion Vibration", "mm/s", 0.0, 14.0, 1.0, 5.2, 0.5, 8.5),
                ],
            },
            {
                "tag": "BRG-301",
                "name": "Mill #1 Top Roller Drive Bearing",
                "type": "Bearing",
                "area": "MILLING",
                "desc": "Phosphor-bronze hydraulic floating journal bearing with pressurized grease line.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("temperature", "Bearing Metal Temp", "°C", 20.0, 100.0, 38.0, 78.0, 28.0, 88.0),
                    ("vibration", "Journal Housing Vibration", "mm/s", 0.0, 15.0, 0.8, 5.0, 0.4, 7.8),
                    ("pressure", "Hydraulic Top Load Pressure", "bar", 50.0, 300.0, 180.0, 260.0, 150.0, 280.0),
                ],
            },
            # Boiler & steam
            {
                "tag": "BLR-401",
                "name": "High Pressure Bagasse Boiler #1",
                "type": "Boiler",
                "area": "BOILER_STEAM",
                "desc": "85 tonnes/hr 45-bar water-tube steam generator fired by mill bagasse.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("pressure", "Main Steam Drum Pressure", "bar", 0.0, 60.0, 38.0, 46.0, 32.0, 50.0),
                    ("temperature", "Superheated Steam Outlet Temp", "°C", 200.0, 480.0, 370.0, 430.0, 340.0, 450.0),
                    ("temperature", "Flue Gas Economizer Temp", "°C", 80.0, 260.0, 140.0, 210.0, 110.0, 235.0),
                ],
            },
            {
                "tag": "STM-402",
                "name": "Main High-Pressure Steam Header",
                "type": "Steam Pipe",
                "area": "BOILER_STEAM",
                "desc": "Carbon steel DN350 process steam manifold routing steam to turbo-alternators and mill turbines.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("pressure", "Header Steam Pressure", "bar", 0.0, 55.0, 36.0, 44.0, 30.0, 48.0),
                    ("temperature", "Steam Flow Temperature", "°C", 150.0, 450.0, 360.0, 420.0, 320.0, 440.0),
                    ("vibration", "Expansion Loop Vibration", "mm/s", 0.0, 8.0, 0.3, 3.2, 0.1, 5.0),
                ],
            },
            {
                "tag": "FAN-401",
                "name": "Boiler Induced Draft (ID) Fan",
                "type": "Fan",
                "area": "BOILER_STEAM",
                "desc": "Variable-speed radial induced draft fan drawing combustion flue gas to electrostatic precipitator.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("motor_speed", "ID Fan Impeller Speed", "RPM", 0.0, 1200.0, 650.0, 1020.0, 500.0, 1120.0),
                    ("vibration", "Fan Drive Bearing Vibration", "mm/s", 0.0, 16.0, 1.2, 6.0, 0.6, 9.2),
                    ("temperature", "Shaft Bearing Temperature", "°C", 20.0, 100.0, 40.0, 75.0, 30.0, 86.0),
                    ("motor_current", "Drive Motor Current", "A", 0.0, 220.0, 70.0, 180.0, 40.0, 205.0),
                ],
            },
            # Juice clarification & evaporation
            {
                "tag": "PMP-501",
                "name": "Mixed Juice Extraction Centrifugal Pump",
                "type": "Pump",
                "area": "JUICE_CLARIFICATION",
                "desc": "Heavy slurry centrifugal pump moving screened raw juice to primary heat exchangers.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("pressure", "Discharge Pressure", "bar", 0.0, 12.0, 3.5, 7.5, 2.2, 9.0),
                    ("motor_current", "Pump Motor Current", "A", 0.0, 90.0, 30.0, 72.0, 18.0, 82.0),
                    ("vibration", "Pump Volute Casing Vibration", "mm/s", 0.0, 12.0, 0.8, 4.2, 0.4, 6.8),
                    ("temperature", "Bearing Housing Temperature", "°C", 15.0, 90.0, 35.0, 70.0, 25.0, 80.0),
                ],
            },
            # Centrifugals
            {
                "tag": "CEN-801",
                "name": "Continuous A-Sugar Centrifugal Machine",
                "type": "Centrifugal Machine",
                "area": "CENTRIFUGALS",
                "desc": "Continuous conical basket machine spinning at 1800 RPM to separate high-grade sugar crystals.",
                "status": Equipment.STATUS_RUNNING,
                "sensors": [
                    ("motor_speed", "Basket Rotation Speed", "RPM", 0.0, 2200.0, 1600.0, 1950.0, 1400.0, 2100.0),
                    ("vibration", "Upper Suspension Vibration", "mm/s", 0.0, 18.0, 1.5, 6.8, 0.8, 11.5),
                    ("temperature", "Main Spindle Bearing Temp", "°C", 20.0, 95.0, 40.0, 76.0, 30.0, 86.0),
                    ("motor_current", "Spindle Motor Current", "A", 0.0, 160.0, 45.0, 125.0, 25.0, 145.0),
                ],
            },
        ]

        equip_map = {}
        for edata in equipment_data:
            eq = Equipment.query.filter_by(equipment_tag=edata["tag"]).first()
            area = area_map[edata["area"]]
            if not eq:
                eq = Equipment(
                    equipment_tag=edata["tag"],
                    name=edata["name"],
                    equipment_type=edata["type"],
                    plant_area_id=area.id,
                    description=edata["desc"],
                    operating_status=edata["status"],
                    installation_date=date(2021, 6, 15),
                    maintenance_info="Regular 500h service interval; factory greased; vibration baseline documented.",
                    is_active=True,
                )
                db.session.add(eq)
                db.session.flush()
                print(f"Created equipment: {eq.equipment_tag} - {eq.name}")

                # Create Sensor Definitions
                for stype, sname, unit, min_acc, max_acc, warn_min, warn_max, crit_min, crit_max in edata["sensors"]:
                    sdef = SensorDefinition(
                        equipment_id=eq.id,
                        sensor_type=stype,
                        sensor_name=sname,
                        unit=unit,
                        min_acceptable=min_acc,
                        max_acceptable=max_acc,
                        warning_min=warn_min,
                        warning_max=warn_max,
                        critical_min=crit_min,
                        critical_max=crit_max,
                        is_enabled=True,
                    )
                    db.session.add(sdef)
            equip_map[edata["tag"]] = eq

        db.session.commit()

        # ── 4. Baseline Maintenance Schedules ───────────────────────────────
        schedules_data = [
            ("CV-101", "Weekly Conveyor Alignment & Belt Tension Inspection", 7, 3),
            ("CRU-201", "Bi-Weekly Hammer Tip Wear & Rotor Dynamic Balance", 14, 5),
            ("MTR-201", "Monthly Motor Insulation Resistance & Winding Megger Test", 30, 12),
            ("GBX-301", "Monthly Gearbox Oil Viscosity & Particle Spectrometry", 30, 18),
            ("BLR-401", "Quarterly Safety Relief Valve Calibration & Sootblower Check", 90, 45),
            ("FAN-401", "Monthly Induced Draft Fan Dynamic Balancing & Bearing Lube", 30, 8),
            ("CEN-801", "Bi-Weekly Basket Screen Inspection & Spindle Vibration Audit", 14, 6),
        ]

        for tag, title, interval, days_due in schedules_data:
            eq = equip_map.get(tag)
            if eq:
                existing_sched = MaintenanceSchedule.query.filter_by(equipment_id=eq.id, title=title).first()
                if not existing_sched:
                    sched = MaintenanceSchedule(
                        equipment_id=eq.id,
                        title=title,
                        description=f"Preventive schedule for {eq.name}. Check operational limits and mechanical integrity.",
                        interval_days=interval,
                        next_due_date=date.today() + timedelta(days=days_due),
                        assigned_to_id=user_map["admin"].id,
                        is_active=True,
                    )
                    db.session.add(sched)

        db.session.commit()

        # ── 5. Initial Audit Log Entry ──────────────────────────────────────
        db.session.add(
            AuditLog(
                user_id=user_map["admin"].id,
                action="INITIALIZE_DATABASE",
                entity_type="SYSTEM",
                entity_id=None,
                details="Initialised sugar factory assets, sensor definitions, users, and baseline maintenance schedules.",
                ip_address="127.0.0.1",
            )
        )

        db.session.commit()
        print("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
