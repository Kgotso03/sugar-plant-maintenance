"""
Simulation Engine for Sugar Factory Equipment Telemetry.
Generates realistic, physically-plausible synthetic sensor streams
under normal operating conditions and 12 distinct fault scenarios.
All generated data is explicitly flagged as SIMULATED DATA.
"""
import random
import threading
import time
from datetime import datetime, timezone
from extensions import db
from models.simulation import SimulationRun
from models.equipment import Equipment
from models.sensor import SensorDefinition, SensorReading
from services.threshold_engine import ThresholdEngine


class SimulationEngine:
    _instance = None
    _lock = threading.Lock()
    _step_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, app=None):
        if getattr(self, "_initialized", False):
            if app is not None:
                self.app = app
            return
        self.app = app
        self.is_running = False
        self.is_paused = False
        self.current_run_id = None
        self.scenario = SimulationRun.SCENARIO_NORMAL
        self.speed_factor = 1.0
        self.selected_equipment_id = None
        self.step_count = 0
        self.degradation_step = 0
        self._thread = None
        self._stop_event = threading.Event()
        self._initialized = True

    def init_app(self, app):
        self.app = app

    def get_status(self):
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_run_id": self.current_run_id,
            "scenario": self.scenario,
            "scenario_label": SimulationRun.SCENARIOS.get(self.scenario, self.scenario),
            "speed_factor": self.speed_factor,
            "selected_equipment_id": self.selected_equipment_id,
            "step_count": self.step_count,
        }

    def start(self, scenario=SimulationRun.SCENARIO_NORMAL, speed_factor=1.0, equipment_id=None, user_id=None):
        with self._lock:
            if self.is_running and not self.is_paused:
                # Update existing run parameters if already running
                self.scenario = scenario
                self.speed_factor = max(0.2, min(float(speed_factor), 5.0))
                self.selected_equipment_id = equipment_id
                if self.current_run_id and self.app:
                    with self.app.app_context():
                        run = db.session.get(SimulationRun, self.current_run_id)
                        if run:
                            run.scenario = scenario
                            run.speed_factor = self.speed_factor
                            run.selected_equipment_id = equipment_id
                            db.session.commit()
                return self.get_status()

            if self.is_paused:
                self.resume()
                self.scenario = scenario
                self.speed_factor = max(0.2, min(float(speed_factor), 5.0))
                self.selected_equipment_id = equipment_id
                return self.get_status()

            # Start new simulation run
            self.scenario = scenario
            self.speed_factor = max(0.2, min(float(speed_factor), 5.0))
            self.selected_equipment_id = equipment_id
            self.step_count = 0
            self.degradation_step = 0
            self._stop_event.clear()

            if self.app:
                with self.app.app_context():
                    run = SimulationRun(
                        name=f"Simulation - {SimulationRun.SCENARIOS.get(scenario, scenario)}",
                        scenario=scenario,
                        status=SimulationRun.STATUS_RUNNING,
                        speed_factor=self.speed_factor,
                        selected_equipment_id=equipment_id,
                        started_at=datetime.now(timezone.utc),
                        created_by_id=user_id,
                    )
                    db.session.add(run)
                    db.session.commit()
                    self.current_run_id = run.id

            self.is_running = True
            self.is_paused = False

            # Spawn controlled background worker
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()
            return self.get_status()

    def pause(self):
        with self._lock:
            if self.is_running and not self.is_paused:
                self.is_paused = True
                if self.current_run_id and self.app:
                    with self.app.app_context():
                        run = db.session.get(SimulationRun, self.current_run_id)
                        if run:
                            run.status = SimulationRun.STATUS_PAUSED
                            db.session.commit()
        return self.get_status()

    def resume(self):
        with self._lock:
            if self.is_running and self.is_paused:
                self.is_paused = False
                if self.current_run_id and self.app:
                    with self.app.app_context():
                        run = db.session.get(SimulationRun, self.current_run_id)
                        if run:
                            run.status = SimulationRun.STATUS_RUNNING
                            db.session.commit()
        return self.get_status()

    def stop(self):
        with self._lock:
            if not self.is_running:
                return self.get_status()

            self.is_running = False
            self.is_paused = False
            self._stop_event.set()

            if self.current_run_id and self.app:
                with self.app.app_context():
                    run = db.session.get(SimulationRun, self.current_run_id)
                    if run:
                        run.status = SimulationRun.STATUS_STOPPED
                        run.ended_at = datetime.now(timezone.utc)
                        db.session.commit()

            self.current_run_id = None

        # Wait for worker thread to stop cleanly
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        return self.get_status()

    def _worker_loop(self):
        """Background thread executing periodic simulation steps."""
        while not self._stop_event.is_set() and self.is_running:
            if not self.is_paused:
                try:
                    if self.app:
                        with self.app.app_context():
                            self._execute_step()
                except Exception as e:
                    print(f"Error in simulation step: {e}")

            # Sleep between steps, scaled inversely by speed_factor
            # Base interval is 2.5 seconds
            sleep_duration = max(0.5, 2.5 / self.speed_factor)
            time.sleep(sleep_duration)

    def execute_step_once(self):
        """Allows synchronous execution of a single simulation tick."""
        if self.app:
            with self.app.app_context():
                return self._execute_step()
        return []

    def _execute_step(self):
        """Core step logic: generates telemetry for equipment and applies threshold checks."""
        with self._step_lock:
            self.step_count += 1
            if self.scenario == SimulationRun.SCENARIO_GRADUAL_DEGRADATION:
                self.degradation_step += 1

            # Query targets
            if self.selected_equipment_id:
                targets = Equipment.query.filter_by(id=self.selected_equipment_id, is_active=True).all()
            else:
                targets = Equipment.query.filter_by(is_active=True).all()

            recorded_items = []
            now = datetime.now(timezone.utc)

            for equip in targets:
                for sdef in equip.sensors:
                    if not sdef.is_enabled:
                        continue

                    val = self._generate_sensor_value(equip, sdef, self.scenario, self.degradation_step)
                    reading, alert = ThresholdEngine.process_reading(
                        equipment=equip,
                        sensor_def=sdef,
                        value=val,
                        simulation_run_id=self.current_run_id,
                        recorded_at=now,
                    )
                    recorded_items.append(reading)

            db.session.commit()
            return recorded_items

    def _generate_sensor_value(
        self,
        equipment: Equipment,
        sdef: SensorDefinition,
        scenario: str,
        degradation_step: int = 0,
    ) -> float:
        """
        Synthesizes realistic sensor readings based on equipment type, sensor type,
        configured normal range, and active fault scenario.
        """
        stype = sdef.sensor_type
        # Baseline center calculation from warning limits or min/max
        low = sdef.warning_min if sdef.warning_min is not None else sdef.min_acceptable
        high = sdef.warning_max if sdef.warning_max is not None else sdef.max_acceptable
        nominal = (low + high) / 2.0
        span = high - low

        # Natural operating flutter (+- 3-5%)
        noise = random.gauss(0, span * 0.03)
        val = nominal + noise

        # Apply specific fault scenarios
        if scenario == SimulationRun.SCENARIO_NORMAL:
            pass

        elif scenario == SimulationRun.SCENARIO_CONVEYOR_MALFUNCTION:
            if "Conveyor" in equipment.equipment_type:
                if stype == SensorDefinition.TYPE_BELT_SPEED:
                    # Erratic slipping belt
                    val = max(0.1, low * 0.4 + random.uniform(-0.3, 0.2))
                elif stype == SensorDefinition.TYPE_VIBRATION:
                    # Severe belt flutter/flapping
                    val = (sdef.critical_max or high) * 1.25 + random.uniform(0.5, 2.0)

        elif scenario == SimulationRun.SCENARIO_CONVEYOR_BELT_STOPPED_MOTOR_RUNNING:
            if "Conveyor" in equipment.equipment_type:
                if stype == SensorDefinition.TYPE_BELT_SPEED:
                    val = 0.0  # Belt completely stalled
                elif stype == SensorDefinition.TYPE_MOTOR_CURRENT:
                    # Stalled rotor high current draw
                    val = (sdef.critical_max or high) * 1.35 + random.uniform(5, 15)
                elif stype == SensorDefinition.TYPE_TEMPERATURE:
                    val = (sdef.critical_max or high) * 1.1 + random.uniform(1, 4)

        elif scenario == SimulationRun.SCENARIO_HIGH_TEMPERATURE:
            if stype == SensorDefinition.TYPE_TEMPERATURE:
                val = (sdef.critical_max or high) * 1.18 + random.uniform(1.0, 5.0)

        elif scenario == SimulationRun.SCENARIO_LOW_TEMPERATURE:
            if stype == SensorDefinition.TYPE_TEMPERATURE:
                val = max(sdef.min_acceptable, (sdef.critical_min or low) * 0.7 - random.uniform(2.0, 6.0))

        elif scenario == SimulationRun.SCENARIO_EXCESSIVE_VIBRATION:
            if stype == SensorDefinition.TYPE_VIBRATION:
                val = (sdef.critical_max or high) * 1.4 + random.uniform(1.0, 4.0)

        elif scenario == SimulationRun.SCENARIO_HIGH_PRESSURE:
            if stype == SensorDefinition.TYPE_PRESSURE:
                val = (sdef.critical_max or high) * 1.22 + random.uniform(1.0, 4.0)

        elif scenario == SimulationRun.SCENARIO_LOW_PRESSURE:
            if stype == SensorDefinition.TYPE_PRESSURE:
                val = max(sdef.min_acceptable, (sdef.critical_min or low) * 0.6 - random.uniform(0.5, 2.0))

        elif scenario == SimulationRun.SCENARIO_HIGH_MOTOR_CURRENT:
            if stype == SensorDefinition.TYPE_MOTOR_CURRENT:
                val = (sdef.critical_max or high) * 1.3 + random.uniform(5.0, 15.0)

        elif scenario == SimulationRun.SCENARIO_REDUCED_MOTOR_SPEED:
            if stype == SensorDefinition.TYPE_MOTOR_SPEED:
                val = max(sdef.min_acceptable, (sdef.critical_min or low) * 0.75 - random.uniform(20, 80))

        elif scenario == SimulationRun.SCENARIO_GRADUAL_DEGRADATION:
            # Linear drift over 30 steps toward critical
            factor = min(1.0, degradation_step / 30.0)
            if stype in (SensorDefinition.TYPE_TEMPERATURE, SensorDefinition.TYPE_VIBRATION, SensorDefinition.TYPE_MOTOR_CURRENT):
                target = (sdef.critical_max or high) * 1.25
                val = nominal + (target - nominal) * factor + random.gauss(0, span * 0.02)

        elif scenario == SimulationRun.SCENARIO_MULTIPLE_FAULTS:
            # Simultaneous temperature surge, excessive vibration, and high current
            if stype == SensorDefinition.TYPE_TEMPERATURE:
                val = (sdef.critical_max or high) * 1.15 + random.uniform(2.0, 6.0)
            elif stype == SensorDefinition.TYPE_VIBRATION:
                val = (sdef.critical_max or high) * 1.35 + random.uniform(1.0, 3.5)
            elif stype == SensorDefinition.TYPE_MOTOR_CURRENT:
                val = (sdef.critical_max or high) * 1.25 + random.uniform(4.0, 12.0)

        # Enforce realistic non-negative physical bounds where applicable
        if sdef.min_acceptable >= 0:
            val = max(sdef.min_acceptable * 0.8, val)

        return round(val, 2)


# Module-level singleton
simulator = SimulationEngine()
