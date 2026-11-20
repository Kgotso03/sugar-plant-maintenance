"""
Random Forest Model Training and Evaluation Pipeline.
Trains an ensemble failure risk predictor on synthetic sugar plant telemetry.
Evaluates accuracy, precision, recall, F1, and confusion matrix on held-out test data.
Avoids data leakage by fitting preprocessors and estimators strictly on train split.
"""
import os
import sys
import json
import joblib

# Ensure root directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from ml.synthetic_data import generate_synthetic_maintenance_dataset

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_store")
MODEL_PATH = os.path.join(MODEL_DIR, "rf_failure_model.joblib")
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

TARGET_LABELS = {0: "low", 1: "medium", 2: "high"}


def train_and_save_model(n_samples: int = 6000, random_state: int = 42):
    """
    Trains and saves Random Forest model with full evaluation metrics.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"Generating {n_samples} synthetic training telemetry records...")
    df = generate_synthetic_maintenance_dataset(n_samples=n_samples, random_state=random_state)

    X = df[FEATURE_NAMES]
    y = df["risk_label"]

    # Strict held-out test split (25%) to prevent data leakage
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state, stratify=y
    )

    print(f"Training set: {len(X_train)} samples | Test set: {len(X_test)} samples")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Predictions on held-out test set
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    # Evaluation metrics
    cr_dict = classification_report(
        y_test,
        y_pred,
        target_names=["low", "medium", "high"],
        output_dict=True,
    )
    cm = confusion_matrix(y_test, y_pred).tolist()

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted"
    )

    feature_importances = dict(
        zip(FEATURE_NAMES, [round(float(x), 4) for x in model.feature_importances_])
    )

    metrics = {
        "model_type": "Random Forest Classifier",
        "model_version": "RandomForest-v1.0",
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "n_samples_total": len(df),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "overall_accuracy": round(float(cr_dict["accuracy"]), 4),
        "weighted_precision": round(float(precision), 4),
        "weighted_recall": round(float(recall), 4),
        "weighted_f1": round(float(f1), 4),
        "per_class": {
            "low": {
                "precision": round(cr_dict["low"]["precision"], 4),
                "recall": round(cr_dict["low"]["recall"], 4),
                "f1_score": round(cr_dict["low"]["f1-score"], 4),
                "support": cr_dict["low"]["support"],
            },
            "medium": {
                "precision": round(cr_dict["medium"]["precision"], 4),
                "recall": round(cr_dict["medium"]["recall"], 4),
                "f1_score": round(cr_dict["medium"]["f1-score"], 4),
                "support": cr_dict["medium"]["support"],
            },
            "high": {
                "precision": round(cr_dict["high"]["precision"], 4),
                "recall": round(cr_dict["high"]["recall"], 4),
                "f1_score": round(cr_dict["high"]["f1-score"], 4),
                "support": cr_dict["high"]["support"],
            },
        },
        "confusion_matrix": cm,
        "feature_importances": feature_importances,
        "demonstration_notice": (
            "NOTICE: Trained on synthetic demonstration data. Real industrial deployment "
            "requires engineering validation and historical physical sensor data."
        ),
    }

    # Save artifacts
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("Model successfully trained and persisted:")
    print(f" -> Accuracy: {metrics['overall_accuracy']:.2%}")
    print(f" -> Weighted F1: {metrics['weighted_f1']:.4f}")
    return model, metrics


if __name__ == "__main__":
    train_and_save_model()
