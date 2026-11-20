# 🏭 Sugar Plant Predictive Maintenance System

A complete, full-stack web application that **simulates a sugar processing plant**, monitors equipment health using synthetic sensor telemetry, detects faults, predicts equipment failures using machine learning, and manages maintenance operations.

> **⚠️ IMPORTANT DISCLAIMER — SIMULATION ONLY**
> All sensor readings and operational data in this system are **synthetically generated** and explicitly labelled as **SIMULATED DATA**. This system is designed for academic demonstration and software development training. Demonstration thresholds provided are NOT approved industrial safety limits. Any real-world deployment would require representative historical plant data, calibrated sensor hardware, and validation by qualified sugar plant engineers.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Database Setup](#database-setup)
7. [Machine Learning Model](#machine-learning-model)
8. [Running the Application](#running-the-application)
9. [Default User Accounts](#default-user-accounts)
10. [Feature Overview](#feature-overview)
11. [Running Tests](#running-tests)
12. [Project Structure](#project-structure)
13. [Troubleshooting](#troubleshooting)
14. [Safety Disclaimers](#safety-disclaimers)

---

## Project Overview

The Sugar Plant Predictive Maintenance System provides:

- **Real-time equipment monitoring** via a configurable simulation engine generating synthetic sensor streams.
- **12 distinct fault scenarios** including belt faults, high temperature, excessive vibration, pressure anomalies, and motor current spikes.
- **Configurable threshold detection** with Normal / Warning / Critical alert levels and alert deduplication.
- **Random Forest ML failure-risk prediction** with training, evaluation, and per-equipment risk scoring.
- **Complete maintenance management**: work orders, preventive maintenance schedules, and repair history.
- **Interactive dashboard** with live Chart.js charts updated during simulation.
- **Role-based access control** for Administrators, Maintenance Engineers, Technicians, and Plant Managers.
- **Reports and CSV export** covering sensor history, faults, predictions, work orders, and maintenance costs.
- **Progressive Web App (PWA)** support for offline capability and mobile installation.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ with Flask |
| Database | MySQL 8.x (or MariaDB 10.11+) via WAMP/XAMPP |
| ORM | Flask-SQLAlchemy / SQLAlchemy 2.x |
| Frontend | HTML5, CSS3, JavaScript (ES2020) |
| Charts | Chart.js 4.x (CDN) |
| Data processing | pandas, NumPy |
| Machine learning | scikit-learn (Random Forest classifier) |
| Authentication | Flask sessions with bcrypt password hashing |
| Configuration | python-dotenv (`.env` file) |
| Testing | pytest with SQLite in-memory test database |

---

## System Architecture

```
sugar_plant_maintenance/
├── app.py                    ← Flask application factory & entry point
├── config.py                 ← Dev / Test / Prod configuration classes
├── extensions.py             ← SQLAlchemy db singleton
├── .env                      ← Environment variables (not committed)
├── requirements.txt          ← Python dependencies
│
├── models/                   ← SQLAlchemy data models
│   ├── user.py               ← User accounts & RBAC roles
│   ├── plant.py              ← Plant areas
│   ├── equipment.py          ← Equipment assets & types
│   ├── sensor.py             ← Sensor definitions & readings
│   ├── simulation.py         ← Simulation run records
│   ├── alert.py              ← Fault alerts & acknowledgements
│   ├── prediction.py         ← ML failure predictions
│   ├── maintenance.py        ← Work orders, PM schedules, repair history
│   └── audit.py              ← Audit trail
│
├── services/                 ← Business logic layer
│   ├── auth_service.py       ← Login, logout, RBAC decorators
│   ├── simulator.py          ← Singleton simulation engine (12 fault scenarios)
│   ├── threshold_engine.py   ← Threshold evaluation & alert generation
│   ├── alert_service.py      ← Alert acknowledgement & resolution
│   ├── prediction_engine.py  ← ML model inference
│   ├── maintenance_service.py← Work order & schedule management
│   └── audit_service.py      ← Action logging
│
├── routes/                   ← Flask blueprints (one per feature area)
│   ├── auth.py               ← Login / logout / profile
│   ├── dashboard.py          ← Main dashboard & live chart APIs
│   ├── plant_areas.py        ← Plant area CRUD
│   ├── equipment.py          ← Equipment CRUD & telemetry API
│   ├── simulation.py         ← Simulation control & status API
│   ├── sensors.py            ← Sensor threshold configuration & trends
│   ├── alerts.py             ← Alert list & management
│   ├── predictions.py        ← ML predictions & model retraining
│   ├── maintenance.py        ← Work orders, PM schedules, history
│   ├── reports.py            ← Reports & CSV export
│   ├── users.py              ← User management (admin only)
│   └── settings.py           ← System settings & audit trail
│
├── ml/                       ← Machine learning module
│   ├── synthetic_data.py     ← 5000-sample labelled dataset generator
│   ├── train_model.py        ← Model training & persistence (joblib)
│   ├── evaluate_model.py     ← Metrics: precision, recall, F1, confusion matrix
│   └── model_store/          ← Trained model & metrics JSON
│
├── database/
│   ├── schema.sql            ← Full CREATE TABLE reference (SQLAlchemy auto-creates)
│   └── seed_data.py          ← Demo users, plant areas, equipment, PM schedules
│
├── static/
│   ├── css/style.css         ← Industrial design system
│   ├── js/main.js            ← Sidebar, PWA registration, UI helpers
│   ├── manifest.json         ← PWA manifest
│   └── sw.js                 ← Service worker (static asset cache)
│
├── templates/                ← Jinja2 HTML templates
│   └── base.html             ← Shared layout with RBAC-aware navigation
│
└── tests/
    ├── test_health.py        ← Smoke tests (health endpoints, auth, static files)
    └── test_full_system.py   ← 10 comprehensive integration tests
```

---

## Prerequisites

Install the following before proceeding:

1. **Python 3.11 or newer** — [python.org/downloads](https://www.python.org/downloads/)  
   Verify: `python --version`

2. **WAMP Server** (recommended) or **XAMPP** — provides MySQL 8.x on Windows.  
   Download: [wampserver.com](https://www.wampserver.com/) | [apachefriends.org](https://www.apachefriends.org/)

3. **Git** (optional) — [git-scm.com](https://git-scm.com/)

4. **VS Code** (optional, recommended) — [code.visualstudio.com](https://code.visualstudio.com/)

---

## Installation

### Step 1 — Clone or extract the project

```powershell
cd C:\
git clone <repository-url> sugar_plant_maintenance
cd sugar_plant_maintenance
```

Or extract the ZIP archive to `C:\sugar_plant_maintenance\`.

### Step 2 — Create and activate a Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If you see a PowerShell execution policy error, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Copy the example configuration file and edit it:

```powershell
copy .env.example .env
notepad .env
```

Set these values in `.env`:

```ini
# Flask
SECRET_KEY=change-this-to-a-long-random-secret-key
FLASK_ENV=development
FLASK_DEBUG=1

# MySQL connection — adjust username and password to match your WAMP/XAMPP setup
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:@127.0.0.1:3306/sugar_plant_maintenance
```

> **Default WAMP MySQL credentials:** username `root`, no password, port `3306`.  
> If you set a root password in MySQL, include it: `mysql+pymysql://root:yourpassword@127.0.0.1:3306/sugar_plant_maintenance`

---

## Database Setup

### Step 1 — Start MySQL

In WAMP, click the WAMP icon in the system tray and start all services (green icon).  
In XAMPP, open the XAMPP Control Panel and click **Start** next to MySQL.

Verify MySQL is running on port 3306:

```powershell
netstat -an | findstr 3306
```

### Step 2 — Create the database

Open a MySQL command prompt or use phpMyAdmin:

```sql
CREATE DATABASE IF NOT EXISTS sugar_plant_maintenance
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

Or via PowerShell (adjust path for your WAMP version):

```powershell
& "C:\wamp64\bin\mysql\mysql8.4.7\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS sugar_plant_maintenance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Step 3 — Create tables and seed demo data

The application uses SQLAlchemy to auto-create all tables on first run, but the seed script also creates them and populates demo data:

```powershell
.\.venv\Scripts\python database\seed_data.py
```

Expected output:
```
✓ Tables created
✓ Created plant area: Cane Handling
... (9 plant areas)
✓ Created equipment: CONV-001 Cane Intake Conveyor
... (11 equipment assets)
✓ Created 4 demo users
✓ Seeded 7 preventive maintenance schedules
✓ Database seeding completed successfully
```

---

## Machine Learning Model

Train the Random Forest failure-risk model before first use:

```powershell
.\.venv\Scripts\python ml\train_model.py
```

This generates a 5000-sample synthetic dataset, trains a 3-class Random Forest classifier (Low / Medium / High risk), and saves the model to `ml/model_store/rf_failure_model.joblib`.

Evaluate the model:

```powershell
.\.venv\Scripts\python ml\evaluate_model.py
```

> The model achieves near-perfect accuracy on synthetic data because the data is generated by the same process it learns from. **This does not indicate real-world accuracy.** A production deployment would require historical fault records from the actual plant and validation by a qualified reliability engineer.

---

## Running the Application

```powershell
.\.venv\Scripts\python app.py
```

The application starts at: **http://127.0.0.1:5000**

Alternatively:

```powershell
$env:FLASK_APP = "app.py"; .\.venv\Scripts\flask run --host=0.0.0.0 --port=5000
```

Open your browser to **http://127.0.0.1:5000** and log in with one of the demo accounts below.

---

## System Administrator Account

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| `admin` | `Admin123!` | Administrator | Full administrative control: equipment, thresholds, live monitoring, users, ML training, reports |

> **Change this password immediately** before deploying to any production or networked environment. Additional users and roles (Engineers, Technicians, Managers) can be created as needed from the **User Management** panel by the administrator.

---

## Feature Overview

### Dashboard
The main dashboard (`/`) shows live KPI cards and 8 Chart.js charts:
- Equipment status distribution
- Recent fault alerts by severity
- Temperature, vibration, pressure, and motor-current trends
- Failure risk trend
- Work order status breakdown

Charts update automatically every 3 seconds while the simulation is running.

### Simulation Engine (`/simulation`)
- Select a plant scenario (Normal, Belt Fault, High Temperature, Excessive Vibration, etc.)
- Set simulation speed (0.2× to 5× real-time)
- Optionally target a specific equipment asset
- Start / Pause / Resume / Stop controls
- Live telemetry table showing the 20 most recent readings

### Threshold Detection
Configurable per-sensor thresholds (`/sensors`) with:
- Warning and critical bands
- Alert deduplication (no duplicate alerts for consecutive readings of the same fault)
- Acknowledgement and resolution workflow with comments and audit trail

### Machine Learning Predictions (`/predictions`)
- Per-equipment failure risk scores (Low / Medium / High)
- Contributing sensor indicators
- Confusion matrix and classification metrics
- One-click model retraining from the UI (Admin / Engineer roles)

### Maintenance Management (`/work-orders`)
- Work order lifecycle: Open → Assigned → In Progress → Awaiting Parts → Completed / Cancelled
- Link work orders to fault alerts
- Record labour hours, parts used, and maintenance cost
- Preventive maintenance schedules with recurring intervals and completion history
- Full maintenance history per equipment asset

### Reports (`/reports`)
Eight report types with date, equipment, and plant-area filters:
1. Equipment condition summary
2. Sensor reading history
3. Fault and alert report
4. Failure prediction report
5. Maintenance work order report
6. Preventive maintenance compliance
7. Equipment downtime estimates
8. Maintenance cost summary

Export to **CSV** or open a **printable HTML** page.

---

## Running Tests

The test suite uses SQLite in-memory databases — no MySQL connection is required.

```powershell
.\.venv\Scripts\pytest -v
```

Expected result: **14 passed**

Run with coverage (optional, requires `pytest-cov`):

```powershell
pip install pytest-cov
.\.venv\Scripts\pytest --cov=. --cov-report=term-missing
```

---

## Project Structure (key files)

| File | Purpose |
|------|---------|
| `app.py` | Application factory; registers all blueprints and health-check routes |
| `extensions.py` | Shared `db = SQLAlchemy()` singleton |
| `config.py` | Dev / Test / Prod config classes; test mode uses SQLite |
| `.env` | Local environment variables (never commit to version control) |
| `database/seed_data.py` | Run once to populate demo data |
| `ml/train_model.py` | Run once (or on demand) to train and save the ML model |
| `static/manifest.json` | PWA manifest for installability on mobile |
| `static/sw.js` | Service worker for offline static-asset caching |

---

## Troubleshooting

### MySQL not connecting

1. Make sure WAMP or XAMPP is running (green icon in system tray).
2. Check that MySQL is on port 3306: `netstat -an | findstr 3306`
3. Verify the `SQLALCHEMY_DATABASE_URI` in `.env` matches your MySQL credentials.
4. If WAMP runs two MySQL instances (MariaDB on 3307 + MySQL on 3306), ensure the URI uses port 3306.

### PowerShell execution policy error

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `ModuleNotFoundError: No module named 'flask'`

Make sure the virtual environment is activated:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Dashboard charts are empty on first run

Run the seed script, start the simulation from `/simulation`, and wait 10–15 seconds for readings to accumulate. Charts refresh every 3 seconds.

### ML model file not found

Run the training script before starting the app:

```powershell
.\.venv\Scripts\python ml\train_model.py
```

### Port 5000 already in use

Change the port:

```powershell
.\.venv\Scripts\python app.py --port 5001
```

Or set `FLASK_RUN_PORT=5001` in `.env`.

---

## Safety Disclaimers

1. **This is a simulation system.** All sensor readings are synthetically generated. No data in this system originates from physical sensors, PLCs, or industrial control systems.

2. **Demonstration thresholds are NOT industrial safety limits.** The threshold values pre-configured in this system are illustrative defaults for demonstration only. Real operating limits for sugar plant equipment must be determined and approved by qualified plant engineers, equipment manufacturers, and relevant regulatory standards.

3. **ML predictions are advisory only.** The failure-risk model is trained on synthetic data generated by the same simulation engine. Its outputs must not be used to make autonomous maintenance decisions or equipment shutdown commands. Any real-world predictive maintenance system requires historical fault data, sensor calibration records, and engineering validation.

4. **No automated equipment control.** This system does not issue any commands to physical equipment. All actions are confined to this web application and its local database.

5. **Change default passwords** before sharing or deploying this application on any networked environment.

---

## Contributing

This project is an academic demonstration system. Contributions are welcome for:
- Additional fault scenario types
- More equipment types (crystallisers, centrifugals, dryers)
- Integration with real sensor data sources
- Advanced ML models (LSTM, anomaly detection)
- Improved report visualisations

---

## Licence

This project is provided for educational and demonstration purposes. No warranty is provided. Refer to `LICENSE` for details.
