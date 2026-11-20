"""
Dataset Converter for Sugar Plant Predictive Maintenance System.
Converts popular public datasets into the exact CSV format required by train_from_csv.py.

Supported datasets:
  1. IndFD-PM-DT  (Kaggle - closest match, has vibration, temperature, pressure, RPM)
  2. AI4I 2020    (UCI/Kaggle - has temperature, rotational speed, torque)
  3. Sensor Maintenance Dataset (Kaggle - has voltage, current, temperature, vibration)

Usage:
  python ml/convert_dataset.py --dataset indfdt   --file ml/dataset/your_download.csv
  python ml/convert_dataset.py --dataset ai4i     --file ml/dataset/ai4i.csv
  python ml/convert_dataset.py --dataset sensor   --file ml/dataset/sensor_data.csv
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "dataset")
REQUIRED_COLS = [
    "temperature", "temp_trend", "vibration", "vibration_trend",
    "pressure", "pressure_trend", "motor_current", "motor_speed",
    "conveyor_speed", "operating_hours", "recent_alert_count", "risk_label"
]


def compute_trends(df: pd.DataFrame, col: str) -> pd.Series:
    """Compute row-to-row difference as a trend indicator."""
    return df[col].diff().fillna(0.0).round(4)


def label_from_failure(failure_col: pd.Series, soft_threshold: float = 0.3) -> pd.Series:
    """
    Convert a binary failure flag (0/1) or float probability to
    0=Low, 1=Medium, 2=High risk labels.
    """
    if failure_col.dtype == float:
        return failure_col.apply(
            lambda v: 2 if v >= 0.7 else (1 if v >= soft_threshold else 0)
        ).astype(int)
    # Binary 0/1 — treat 0 as Low, 1 as High (no medium)
    return failure_col.astype(int).apply(lambda v: 2 if v == 1 else 0)


# ── Converter 1: IndFD-PM-DT ──────────────────────────────────────────────────
def convert_indfdt(df: pd.DataFrame) -> pd.DataFrame:
    """
    IndFD-PM-DT dataset (Kaggle: search 'IndFD-PM-DT').
    Expected columns (may vary slightly by version):
      Vibration_Level, Temperature_Readings, Pressure_Data,
      Motor_Speed_RPM, Torque, Energy_Consumption, Fault_Label or similar
    """
    # Flexible column detection
    col_map = {}
    for col in df.columns:
        cl = col.lower().replace(" ", "_").replace("-", "_")
        if "temp" in cl:           col_map["temperature"]    = col
        if "vibr" in cl:           col_map["vibration"]      = col
        if "press" in cl:          col_map["pressure"]       = col
        if "current" in cl or "amp" in cl: col_map["motor_current"] = col
        if "rpm" in cl or "motor_speed" in cl or "rotational" in cl: col_map["motor_speed"] = col
        if "conveyor" in cl or "belt" in cl or "speed" in cl and "motor" not in cl: col_map["conveyor_speed"] = col
        if "hour" in cl or "operating" in cl or "wear" in cl: col_map["operating_hours"] = col
        if "fault" in cl or "fail" in cl or "label" in cl or "target" in cl: col_map["risk_label"] = col

    print(f"   Auto-detected column mapping: {col_map}")
    missing = [k for k in ["temperature", "vibration", "risk_label"] if k not in col_map]
    if missing:
        print(f"   [WARN] Could not auto-detect: {missing}")
        print(f"   Available columns: {list(df.columns)}")

    out = pd.DataFrame()
    out["temperature"]    = pd.to_numeric(df[col_map.get("temperature", df.columns[0])], errors="coerce")
    out["vibration"]      = pd.to_numeric(df[col_map.get("vibration", df.columns[1])], errors="coerce")
    out["pressure"]       = pd.to_numeric(df.get(col_map.get("pressure"), pd.Series([38.0]*len(df))), errors="coerce").fillna(38.0)
    out["motor_current"]  = pd.to_numeric(df.get(col_map.get("motor_current"), pd.Series([90.0]*len(df))), errors="coerce").fillna(90.0)
    out["motor_speed"]    = pd.to_numeric(df.get(col_map.get("motor_speed"), pd.Series([1480.0]*len(df))), errors="coerce").fillna(1480.0)
    out["conveyor_speed"] = pd.to_numeric(df.get(col_map.get("conveyor_speed"), pd.Series([1.8]*len(df))), errors="coerce").fillna(1.8)
    out["operating_hours"]= pd.to_numeric(df.get(col_map.get("operating_hours"), pd.Series([1000.0]*len(df))), errors="coerce").fillna(1000.0)

    out["temp_trend"]      = compute_trends(out, "temperature")
    out["vibration_trend"] = compute_trends(out, "vibration")
    out["pressure_trend"]  = compute_trends(out, "pressure")

    if "risk_label" in col_map:
        raw_label = pd.to_numeric(df[col_map["risk_label"]], errors="coerce").fillna(0)
        out["risk_label"] = label_from_failure(raw_label)
    else:
        out["risk_label"] = 0

    out["recent_alert_count"] = 0  # Not available in dataset; default to 0
    return out[REQUIRED_COLS].dropna()


# ── Converter 2: AI4I 2020 ────────────────────────────────────────────────────
def convert_ai4i(df: pd.DataFrame) -> pd.DataFrame:
    """
    AI4I 2020 Predictive Maintenance Dataset.
    Download: https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset
    Kaggle:   https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020

    Original columns:
      Air temperature [K], Process temperature [K],
      Rotational speed [rpm], Torque [Nm], Tool wear [min],
      Machine failure
    """
    out = pd.DataFrame()

    # Temperature: use Process temperature (more relevant), convert K -> C
    temp_col = next((c for c in df.columns if "process" in c.lower() and "temp" in c.lower()), None)
    if not temp_col:
        temp_col = next((c for c in df.columns if "temp" in c.lower()), df.columns[0])

    out["temperature"]    = pd.to_numeric(df[temp_col], errors="coerce") - 273.15  # K to C

    # Vibration: not in AI4I — estimate from Torque deviation
    torque_col = next((c for c in df.columns if "torque" in c.lower()), None)
    if torque_col:
        torque = pd.to_numeric(df[torque_col], errors="coerce").fillna(40.0)
        out["vibration"] = (torque / 40.0) * 2.5  # normalise to ~mm/s range
    else:
        out["vibration"] = 2.5

    # Pressure: not in AI4I — use constant typical value
    out["pressure"] = 38.0

    # Motor current: not in AI4I — estimate from rotational speed deviation
    rpm_col = next((c for c in df.columns if "rotational" in c.lower() or "rpm" in c.lower()), None)
    if rpm_col:
        rpm = pd.to_numeric(df[rpm_col], errors="coerce").fillna(1500.0)
        out["motor_speed"]   = rpm
        out["motor_current"] = 90.0 + (1500.0 - rpm) * 0.05  # inverse relationship
    else:
        out["motor_speed"]   = 1480.0
        out["motor_current"] = 90.0

    out["conveyor_speed"] = 1.8  # Not in AI4I

    # Operating hours: use Tool wear [min] converted to hours
    wear_col = next((c for c in df.columns if "wear" in c.lower()), None)
    if wear_col:
        out["operating_hours"] = pd.to_numeric(df[wear_col], errors="coerce").fillna(0) / 60.0
    else:
        out["operating_hours"] = 1000.0

    out["temp_trend"]      = compute_trends(out, "temperature")
    out["vibration_trend"] = compute_trends(out, "vibration")
    out["pressure_trend"]  = pd.Series([0.0] * len(out))

    # Risk label: use sub-failure flags for 3-class labelling
    # TWF=Tool Wear Failure, HDF=Heat Dissipation, PWF=Power, OSF=Overstrain
    sub_fail_cols = [c for c in df.columns if c in ["TWF", "HDF", "PWF", "OSF", "RNF"]]
    fail_col = next((c for c in df.columns if "machine" in c.lower() and "fail" in c.lower()), None)
    if not fail_col:
        fail_col = next((c for c in df.columns if "fail" in c.lower()), None)

    if fail_col and sub_fail_cols:
        machine_fail = pd.to_numeric(df[fail_col], errors="coerce").fillna(0).astype(int)
        sub_fail_sum = df[sub_fail_cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
        # High = machine actually failed, Medium = sub-indicators triggered, Low = all normal
        labels = []
        for mf, sf in zip(machine_fail, sub_fail_sum):
            if mf == 1:
                labels.append(2)   # High risk
            elif sf >= 1:
                labels.append(1)   # Medium risk
            else:
                labels.append(0)   # Low risk
        out["risk_label"] = labels
    elif fail_col:
        out["risk_label"] = label_from_failure(pd.to_numeric(df[fail_col], errors="coerce").fillna(0))
    else:
        out["risk_label"] = 0

    out["recent_alert_count"] = 0
    return out[REQUIRED_COLS].dropna()


# ── Converter 3: Sensor Maintenance Dataset ───────────────────────────────────
def convert_sensor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sensor Maintenance Dataset (Kaggle: search 'Sensor Maintenance Dataset').
    Expected columns: Voltage, Current, Temperature, Power, Vibration, Operational_Status
    """
    out = pd.DataFrame()
    col_l = {c.lower().replace(" ", "_"): c for c in df.columns}

    def get(keys, default=None):
        for k in keys:
            for cl, orig in col_l.items():
                if k in cl:
                    return pd.to_numeric(df[orig], errors="coerce")
        return pd.Series([default] * len(df))

    out["temperature"]    = get(["temp"], 60.0).fillna(60.0)
    out["vibration"]      = get(["vibr"], 2.5).fillna(2.5)
    out["pressure"]       = get(["press"], 38.0).fillna(38.0)
    out["motor_current"]  = get(["current", "amp"], 90.0).fillna(90.0)
    out["motor_speed"]    = get(["rpm", "speed", "rotational"], 1480.0).fillna(1480.0)
    out["conveyor_speed"] = get(["conveyor", "belt"], 1.8).fillna(1.8)
    out["operating_hours"]= get(["hour", "operating", "uptime"], 1000.0).fillna(1000.0)

    out["temp_trend"]      = compute_trends(out, "temperature")
    out["vibration_trend"] = compute_trends(out, "vibration")
    out["pressure_trend"]  = compute_trends(out, "pressure")

    status = get(["status", "label", "fault", "fail", "health"], 0).fillna(0)
    out["risk_label"] = label_from_failure(status)
    out["recent_alert_count"] = 0

    return out[REQUIRED_COLS].dropna()


# ── Entry point ────────────────────────────────────────────────────────────────
CONVERTERS = {
    "indfdt": convert_indfdt,
    "ai4i":   convert_ai4i,
    "sensor": convert_sensor,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert public datasets to Sugar Plant ML format.")
    parser.add_argument("--dataset", choices=list(CONVERTERS.keys()), required=True,
                        help="Which dataset format to convert from")
    parser.add_argument("--file", required=True,
                        help="Path to the downloaded CSV file")
    parser.add_argument("--out", default=None,
                        help="Output CSV path (default: ml/dataset/converted_<dataset>.csv)")
    args = parser.parse_args()

    in_path = os.path.abspath(args.file)
    if not os.path.exists(in_path):
        print(f"[ERROR] File not found: {in_path}")
        sys.exit(1)

    out_path = args.out or os.path.join(OUTPUT_DIR, f"converted_{args.dataset}.csv")

    print(f"Loading: {in_path}")
    df_raw = pd.read_csv(in_path)
    print(f"   {len(df_raw)} rows x {len(df_raw.columns)} columns")
    print(f"   Columns: {list(df_raw.columns)}")

    print(f"\nConverting using '{args.dataset}' converter...")
    converter = CONVERTERS[args.dataset]
    df_out = converter(df_raw)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_out.to_csv(out_path, index=False)

    print(f"\n[OK] Converted {len(df_out)} rows saved to: {out_path}")
    print(f"\nNow train the model with:")
    print(f"   python ml/train_from_csv.py --file {out_path}")

