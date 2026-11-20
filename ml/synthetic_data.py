"""
Synthetic Telemetry Dataset Generator for Sugar Plant Predictive Maintenance ML.
Generates labelled historical operating samples for training failure risk models.
Explicitly labelled as SYNTHETIC DEMONSTRATION DATA.
"""
import numpy as np
import pandas as pd


def generate_synthetic_maintenance_dataset(n_samples: int = 5000, random_state: int = 42) -> pd.DataFrame:
    """
    Generates a realistic multi-feature synthetic dataset representing
    normal operating conditions and progressive equipment distress modes.
    """
    np.random.seed(random_state)

    records = []

    # Distribution: 60% Low Risk, 25% Medium Risk, 15% High Risk
    n_low = int(n_samples * 0.60)
    n_med = int(n_samples * 0.25)
    n_high = n_samples - n_low - n_med

    # 1. Low Risk (Healthy operation)
    for _ in range(n_low):
        records.append({
            "temperature": np.random.normal(55.0, 5.0),
            "temp_trend": np.random.normal(0.0, 0.4),
            "vibration": np.random.normal(2.2, 0.6),
            "vibration_trend": np.random.normal(0.0, 0.1),
            "pressure": np.random.normal(38.0, 2.5),
            "pressure_trend": np.random.normal(0.0, 0.3),
            "motor_current": np.random.normal(85.0, 8.0),
            "motor_speed": np.random.normal(1480.0, 15.0),
            "conveyor_speed": np.random.normal(1.8, 0.1),
            "operating_hours": np.random.uniform(50, 3000),
            "recent_alert_count": int(np.random.choice([0, 1], p=[0.92, 0.08])),
            "risk_label": 0,  # 'low'
        })

    # 2. Medium Risk (Developing wear, lubrication dryout, partial belt slippage)
    for _ in range(n_med):
        records.append({
            "temperature": np.random.normal(74.0, 6.0),
            "temp_trend": np.random.normal(1.2, 0.6),
            "vibration": np.random.normal(4.8, 1.0),
            "vibration_trend": np.random.normal(0.3, 0.15),
            "pressure": np.random.normal(44.0, 4.0),
            "pressure_trend": np.random.normal(0.8, 0.5),
            "motor_current": np.random.normal(115.0, 12.0),
            "motor_speed": np.random.normal(1440.0, 25.0),
            "conveyor_speed": np.random.normal(1.5, 0.2),
            "operating_hours": np.random.uniform(2000, 7000),
            "recent_alert_count": int(np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])),
            "risk_label": 1,  # 'medium'
        })

    # 3. High Risk (Impending catastrophic failure, severe misalignment/cavitation/bearing spalling)
    for _ in range(n_high):
        records.append({
            "temperature": np.random.normal(92.0, 8.0),
            "temp_trend": np.random.normal(3.5, 1.0),
            "vibration": np.random.normal(8.5, 2.0),
            "vibration_trend": np.random.normal(1.2, 0.4),
            "pressure": np.random.normal(51.0, 5.0),
            "pressure_trend": np.random.normal(2.0, 0.8),
            "motor_current": np.random.normal(148.0, 18.0),
            "motor_speed": np.random.normal(1360.0, 50.0),
            "conveyor_speed": np.random.normal(0.9, 0.4),
            "operating_hours": np.random.uniform(5000, 12000),
            "recent_alert_count": int(np.random.choice([2, 3, 4, 5], p=[0.2, 0.4, 0.25, 0.15])),
            "risk_label": 2,  # 'high'
        })

    df = pd.DataFrame(records)
    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return df
