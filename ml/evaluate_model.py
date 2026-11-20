"""
Model Evaluation and Metrics Viewer.
Provides programmatic access to performance metrics, confusion matrices,
and feature importances.
"""
import os
import sys
import json

# Ensure root directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.train_model import METRICS_PATH, MODEL_PATH, train_and_save_model


def get_model_evaluation_metrics():
    """
    Returns existing model metrics or trains model if no checkpoint exists.
    """
    if not os.path.exists(METRICS_PATH) or not os.path.exists(MODEL_PATH):
        _, metrics = train_and_save_model()
        return metrics

    try:
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        _, metrics = train_and_save_model()
        return metrics


if __name__ == "__main__":
    metrics = get_model_evaluation_metrics()
    print("=== MODEL EVALUATION METRICS ===")
    print(f"Algorithm: {metrics['model_type']}")
    print(f"Accuracy: {metrics['overall_accuracy']:.2%}")
    print(f"Weighted Precision: {metrics['weighted_precision']:.4f}")
    print(f"Weighted Recall: {metrics['weighted_recall']:.4f}")
    print(f"Weighted F1: {metrics['weighted_f1']:.4f}")
    print("\nConfusion Matrix [Low, Med, High]:")
    for row in metrics["confusion_matrix"]:
        print(" ", row)
