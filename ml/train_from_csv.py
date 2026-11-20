"""
Train the failure-risk model from a REAL CSV dataset.

Usage:
    python ml/train_from_csv.py --file ml/dataset/your_data.csv
    python ml/train_from_csv.py --file ml/dataset/your_data.csv --samples 6000
    python ml/train_from_csv.py --synthetic   (use built-in synthetic data)

CSV must contain these columns (or use --map to rename):
    temperature, temp_trend, vibration, vibration_trend,
    pressure, pressure_trend, motor_current, motor_speed,
    conveyor_speed, operating_hours, recent_alert_count, risk_label

risk_label values: 0 = Low, 1 = Medium, 2 = High
"""

import os
import sys
import json
import argparse
import joblib
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    accuracy_score,
)

MODEL_DIR   = os.path.join(os.path.dirname(__file__), "model_store")
MODEL_PATH  = os.path.join(MODEL_DIR, "rf_failure_model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

FEATURE_NAMES = [
    "temperature",
    "temp_trend",
    "vibration",
    "vibration_trend",
    "pressure",
    "pressure_trend",
    "motor_current",
    "motor_speed",
    "conveyor_speed",
    "operating_hours",
    "recent_alert_count",
]

LABEL_COLUMN = "risk_label"
TARGET_LABELS = {0: "low", 1: "medium", 2: "high"}


# â”€â”€ Helper: validate the loaded dataframe â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in FEATURE_NAMES + [LABEL_COLUMN] if c not in df.columns]
    if missing:
        print(f"\nâŒ ERROR â€” Missing columns in your CSV: {missing}")
        print(f"   Required columns: {FEATURE_NAMES + [LABEL_COLUMN]}")
        print(f"   Found columns:    {list(df.columns)}")
        print("\n   Use --map to rename columns. Example:")
        print("   python ml/train_from_csv.py --file data.csv --map Temp=temperature Vib=vibration Label=risk_label")
        sys.exit(1)

    invalid_labels = df[~df[LABEL_COLUMN].isin([0, 1, 2])][LABEL_COLUMN].unique()
    if len(invalid_labels) > 0:
        print(f"\nâŒ ERROR â€” risk_label column contains invalid values: {invalid_labels}")
        print("   Allowed values: 0 (Low Risk), 1 (Medium Risk), 2 (High Risk)")
        sys.exit(1)

    # Drop rows with any NaN in feature columns
    before = len(df)
    df = df.dropna(subset=FEATURE_NAMES + [LABEL_COLUMN])
    dropped = before - len(df)
    if dropped > 0:
        print(f"   âš   Dropped {dropped} rows containing missing values.")

    if len(df) < 50:
        print(f"\nâŒ ERROR â€” Only {len(df)} valid rows found. Need at least 50.")
        sys.exit(1)

    return df


# â”€â”€ Main training function â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def train_from_dataframe(df: pd.DataFrame, data_source: str = "real", random_state: int = 42):
    """Trains and saves the Random Forest model from a prepared DataFrame."""

    os.makedirs(MODEL_DIR, exist_ok=True)

    X = df[FEATURE_NAMES].astype(float)
    y = df[LABEL_COLUMN].astype(int)

    label_counts = y.value_counts().to_dict()
    print(f"\n   Risk label distribution:")
    for label_id, label_name in TARGET_LABELS.items():
        count = label_counts.get(label_id, 0)
        pct = 100 * count / len(y)
        print(f"     {label_name.upper():6s} (class {label_id}): {count:5d} samples  ({pct:.1f}%)")

    # Stratified 75/25 train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )
    print(f"\n   Training set : {len(X_train)} samples")
    print(f"   Test set     : {len(X_test)} samples")

    print("\n   Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=14,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    present_classes = sorted(y_test.unique().tolist())
    all_labels = [0, 1, 2]
    all_names  = ["low", "medium", "high"]
    used_names = [all_names[i] for i in present_classes]

    cr_dict = classification_report(
        y_test, y_pred,
        labels=present_classes,
        target_names=used_names,
        output_dict=True,
    )
    # Ensure all three classes exist in the dict (fill missing with zeros)
    for name in all_names:
        if name not in cr_dict:
            cr_dict[name] = {"precision": 0.0, "recall": 0.0, "f1-score": 0.0, "support": 0}
    cm = confusion_matrix(y_test, y_pred).tolist()
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted"
    )
    accuracy = accuracy_score(y_test, y_pred)

    feature_importances = dict(
        zip(FEATURE_NAMES, [round(float(x), 4) for x in model.feature_importances_])
    )

    metrics = {
        "model_type": "Random Forest Classifier",
        "model_version": "RandomForest-v1.0",
        "data_source": data_source,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "n_samples_total": len(df),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "overall_accuracy": round(float(accuracy), 4),
        "weighted_precision": round(float(precision), 4),
        "weighted_recall": round(float(recall), 4),
        "weighted_f1": round(float(f1), 4),
        "per_class": {
            "low":    {k: round(cr_dict["low"][k], 4) if isinstance(cr_dict["low"][k], float) else cr_dict["low"][k]
                       for k in ["precision", "recall", "f1-score", "support"]},
            "medium": {k: round(cr_dict["medium"][k], 4) if isinstance(cr_dict["medium"][k], float) else cr_dict["medium"][k]
                       for k in ["precision", "recall", "f1-score", "support"]},
            "high":   {k: round(cr_dict["high"][k], 4) if isinstance(cr_dict["high"][k], float) else cr_dict["high"][k]
                       for k in ["precision", "recall", "f1-score", "support"]},
        },
        "confusion_matrix": cm,
        "feature_importances": feature_importances,
        "demonstration_notice": (
            "NOTICE: This model was trained on demonstration/synthetic data. "
            "Real industrial deployment requires engineering validation and "
            "representative historical sensor fault records."
        ) if data_source == "synthetic" else (
            f"Trained on real dataset: {data_source}"
        ),
    }

    # Save model and metrics
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n[OK] Model trained and saved to: {MODEL_PATH}")
    print(f"   Accuracy    : {accuracy:.2%}")
    print(f"   Weighted F1 : {f1:.4f}")
    print(f"   Precision   : {precision:.4f}")
    print(f"   Recall      : {recall:.4f}")
    print(f"\n   Confusion Matrix (rows=actual, cols=predicted):")
    print(f"              Low   Mid   High")
    for i, row in enumerate(cm):
        label = ["Low ", "Mid ", "High"][i]
        print(f"   Actual {label}: {row}")
    print(f"\n   Top 3 most important features:")
    sorted_fi = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)
    for feat, imp in sorted_fi[:3]:
        print(f"     {feat:25s}  {imp:.4f}")

    return model, metrics


# â”€â”€ Entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the failure-risk Random Forest model.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Path to your real CSV dataset (e.g. ml/dataset/my_plant_data.csv)"
    )
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Use built-in synthetic data instead of a real CSV"
    )
    parser.add_argument(
        "--samples", type=int, default=6000,
        help="Number of synthetic samples to generate (default: 6000). Ignored when --file is used."
    )
    parser.add_argument(
        "--map", nargs="*", metavar="CSV_COL=REQUIRED_COL",
        help=(
            "Rename CSV columns to match required names.\n"
            "Example: --map Temp=temperature Vibration_mm=vibration Label=risk_label"
        )
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    # â”€â”€ Decide data source â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if args.synthetic or (args.file is None):
        # Synthetic mode
        from ml.synthetic_data import generate_synthetic_maintenance_dataset
        print(f"[DATA] Generating {args.samples} synthetic training records...")
        df = generate_synthetic_maintenance_dataset(
            n_samples=args.samples, random_state=args.seed
        )
        data_source = "synthetic"

    else:
        # Real CSV mode
        csv_path = os.path.abspath(args.file)
        if not os.path.exists(csv_path):
            print(f"\nâŒ ERROR â€” File not found: {csv_path}")
            print(f"   Place your CSV file in: c:\\sugar_plant_maintenance\\ml\\dataset\\")
            sys.exit(1)

        print(f"[CSV] Loading real dataset: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"   Loaded {len(df)} rows Ã— {len(df.columns)} columns")
        print(f"   Columns found: {list(df.columns)}")

        # Apply column renaming if --map was provided
        if args.map:
            rename_map = {}
            for mapping in args.map:
                if "=" not in mapping:
                    print(f"   âš   Ignoring invalid mapping (no '='): {mapping}")
                    continue
                src, dst = mapping.split("=", 1)
                rename_map[src.strip()] = dst.strip()
            if rename_map:
                print(f"   Renaming columns: {rename_map}")
                df = df.rename(columns=rename_map)

        data_source = os.path.basename(csv_path)

    # â”€â”€ Validate and train â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    df = validate_dataframe(df)
    print(f"\n[START] Starting training on {len(df)} validated records...")
    train_from_dataframe(df, data_source=data_source, random_state=args.seed)

