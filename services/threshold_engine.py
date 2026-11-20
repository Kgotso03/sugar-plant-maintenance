"""
Threshold Detection Engine for Sugar Factory Equipment.
Evaluates synthetic sensor telemetry against configurable equipment thresholds.
Applies alert cooldown and deduplication logic.
"""
from datetime import datetime, timezone
from extensions import db
from models.sensor import SensorDefinition, SensorReading
from models.alert import FaultAlert
from models.equipment import Equipment


class ThresholdEngine:
    @staticmethod
    def evaluate_reading(sensor_def: SensorDefinition, value: float) -> str:
        """
        Determines reading status ('normal', 'warning', 'critical')
        based on configured sensor definition thresholds.
        """
        if not sensor_def.is_enabled:
            return SensorReading.STATUS_NORMAL

        # 1. Critical limits check
        if sensor_def.critical_max is not None and value >= sensor_def.critical_max:
            return SensorReading.STATUS_CRITICAL
        if sensor_def.critical_min is not None and value <= sensor_def.critical_min:
            return SensorReading.STATUS_CRITICAL

        # 2. Warning limits check
        if sensor_def.warning_max is not None and value >= sensor_def.warning_max:
            return SensorReading.STATUS_WARNING
        if sensor_def.warning_min is not None and value <= sensor_def.warning_min:
            return SensorReading.STATUS_WARNING

        return SensorReading.STATUS_NORMAL

    @staticmethod
    def process_reading(
        equipment: Equipment,
        sensor_def: SensorDefinition,
        value: float,
        simulation_run_id: int = None,
        recorded_at: datetime = None,
    ) -> tuple[SensorReading, FaultAlert | None]:
        """
        Evaluates a reading, stores it, and triggers or updates an alert if limits are breached.
        Prevents alert flooding using deduplication on active alerts.
        """
        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc)

        status = ThresholdEngine.evaluate_reading(sensor_def, value)

        # Create reading record
        reading = SensorReading(
            equipment_id=equipment.id,
            sensor_definition_id=sensor_def.id,
            simulation_run_id=simulation_run_id,
            sensor_type=sensor_def.sensor_type,
            value=value,
            unit=sensor_def.unit,
            status=status,
            is_simulated=True,
            recorded_at=recorded_at,
        )
        db.session.add(reading)

        alert = None
        if status in (SensorReading.STATUS_WARNING, SensorReading.STATUS_CRITICAL):
            # Check for existing unresolved alert for this equipment and sensor type
            existing_alert = (
                FaultAlert.query.filter_by(
                    equipment_id=equipment.id,
                    sensor_type=sensor_def.sensor_type,
                )
                .filter(FaultAlert.status.in_([FaultAlert.STATUS_ACTIVE, FaultAlert.STATUS_ACKNOWLEDGED]))
                .order_by(FaultAlert.id.desc())
                .first()
            )

            # Determine breach threshold value for record
            if status == SensorReading.STATUS_CRITICAL:
                limit_breached = (
                    sensor_def.critical_max
                    if (sensor_def.critical_max is not None and value >= sensor_def.critical_max)
                    else (sensor_def.critical_min or 0.0)
                )
            else:
                limit_breached = (
                    sensor_def.warning_max
                    if (sensor_def.warning_max is not None and value >= sensor_def.warning_max)
                    else (sensor_def.warning_min or 0.0)
                )

            desc = (
                f"{sensor_def.sensor_name} observed {value:.1f} {sensor_def.unit}, "
                f"exceeding safety threshold ({limit_breached:.1f} {sensor_def.unit})."
            )

            if existing_alert:
                # Deduplicate: update existing active alert rather than flooding the table
                existing_alert.observed_value = value
                existing_alert.last_occurred_at = recorded_at
                if status == SensorReading.STATUS_CRITICAL and existing_alert.severity != FaultAlert.SEVERITY_CRITICAL:
                    existing_alert.severity = FaultAlert.SEVERITY_CRITICAL
                    existing_alert.description = desc
                alert = existing_alert
            else:
                # New alert instance
                alert = FaultAlert(
                    equipment_id=equipment.id,
                    sensor_definition_id=sensor_def.id,
                    simulation_run_id=simulation_run_id,
                    sensor_type=sensor_def.sensor_type,
                    observed_value=value,
                    configured_limit=limit_breached,
                    severity=FaultAlert.SEVERITY_CRITICAL if status == SensorReading.STATUS_CRITICAL else FaultAlert.SEVERITY_WARNING,
                    description=desc,
                    status=FaultAlert.STATUS_ACTIVE,
                    last_occurred_at=recorded_at,
                    created_at=recorded_at,
                )
                db.session.add(alert)
                db.session.flush()

        return reading, alert
