"""
Simulation Control Room and Telemetry Stream Routes.
All telemetry is explicitly identified and handled as SIMULATED DATA.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models.simulation import SimulationRun
from models.equipment import Equipment
from models.sensor import SensorReading
from services.simulator import simulator
from services.auth_service import login_required, get_current_user
from services.audit_service import log_action

simulation_bp = Blueprint("simulation", __name__)


@simulation_bp.route("/simulation")
@login_required
def index():
    equipment_list = Equipment.query.filter_by(is_active=True).all()
    recent_runs = SimulationRun.query.order_by(SimulationRun.id.desc()).limit(10).all()
    current_status = simulator.get_status()

    return render_template(
        "simulation/index.html",
        equipment_list=equipment_list,
        scenarios=SimulationRun.SCENARIOS,
        recent_runs=recent_runs,
        sim_status=current_status,
    )


@simulation_bp.route("/api/simulation/status")
@login_required
def api_status():
    status = simulator.get_status()
    # Fetch latest 10 readings generated
    recent = (
        SensorReading.query.order_by(SensorReading.id.desc())
        .limit(10)
        .all()
    )
    return jsonify({
        "status": status,
        "recent_readings": [r.to_dict() for r in recent],
    })


@simulation_bp.route("/api/simulation/start", methods=["POST"])
@login_required
def api_start():
    user = get_current_user()
    data = request.get_json() or request.form

    scenario = data.get("scenario", SimulationRun.SCENARIO_NORMAL)
    speed_factor = float(data.get("speed_factor", 1.0))
    equipment_id = data.get("equipment_id")
    equipment_id = int(equipment_id) if equipment_id and str(equipment_id).isdigit() and int(equipment_id) > 0 else None

    result = simulator.start(
        scenario=scenario,
        speed_factor=speed_factor,
        equipment_id=equipment_id,
        user_id=user.id if user else None,
    )
    log_action("START_SIMULATION", "SimulationRun", simulator.current_run_id, f"Scenario: {scenario}, Speed: {speed_factor}x")
    return jsonify({"success": True, "status": result})


@simulation_bp.route("/api/simulation/pause", methods=["POST"])
@login_required
def api_pause():
    result = simulator.pause()
    log_action("PAUSE_SIMULATION", "SimulationRun", simulator.current_run_id, "Simulation paused")
    return jsonify({"success": True, "status": result})


@simulation_bp.route("/api/simulation/resume", methods=["POST"])
@login_required
def api_resume():
    result = simulator.resume()
    log_action("RESUME_SIMULATION", "SimulationRun", simulator.current_run_id, "Simulation resumed")
    return jsonify({"success": True, "status": result})


@simulation_bp.route("/api/simulation/stop", methods=["POST"])
@login_required
def api_stop():
    run_id = simulator.current_run_id
    result = simulator.stop()
    log_action("STOP_SIMULATION", "SimulationRun", run_id, "Simulation stopped")
    return jsonify({"success": True, "status": result})


@simulation_bp.route("/api/simulation/step", methods=["POST"])
@login_required
def api_step():
    """Executes a single discrete simulation step on demand."""
    recorded = simulator.execute_step_once()
    return jsonify({
        "success": True,
        "steps_generated": len(recorded),
        "readings": [r.to_dict() for r in recorded[:10]],
    })
