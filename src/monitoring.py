"""
Runtime monitoring: prediction logging, data drift detection, confidence tracking.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any

LOGS_DIR = Path(__file__).parent.parent / "logs"
PREDICTIONS_LOG = LOGS_DIR / "predictions.csv"


def _ensure_logs_dir():
    LOGS_DIR.mkdir(exist_ok=True)


def log_prediction(
    input_params: dict,
    output_material: str,
    score: float,
    confidence: float,
    risk_category: str,
    model_version: str = "unknown",
    pipeline_latency_ms: float = 0,
):
    """Log every prediction for audit and monitoring."""
    _ensure_logs_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "material": output_material,
        "score": round(score, 4),
        "confidence": round(confidence, 4),
        "risk_category": risk_category,
        "model_version": model_version,
        "latency_ms": round(pipeline_latency_ms, 1),
        "target_tensile": input_params.get("target_tensile_strength", ""),
        "target_wvtr": input_params.get("target_wvtr", ""),
        "min_biocompat": input_params.get("min_biocompatibility", ""),
    }
    df = pd.DataFrame([entry])
    if PREDICTIONS_LOG.exists():
        df.to_csv(PREDICTIONS_LOG, mode='a', header=False, index=False)
    else:
        df.to_csv(PREDICTIONS_LOG, index=False)


def detect_data_drift(
    current_data: pd.DataFrame,
    reference_data: pd.DataFrame,
    feature_cols: list[str],
    threshold: float = 0.3,
) -> dict[str, Any]:
    """
    Detect drift between current and reference data using
    normalized mean difference per feature.
    """
    drift_report = {"drifted_features": [], "details": {}}

    for col in feature_cols:
        if col not in current_data.columns or col not in reference_data.columns:
            continue

        ref_mean = reference_data[col].mean()
        ref_std = reference_data[col].std()
        cur_mean = current_data[col].mean()

        if ref_std == 0:
            shift = 0.0
        else:
            shift = abs(cur_mean - ref_mean) / ref_std

        drift_report["details"][col] = {
            "ref_mean": round(ref_mean, 3),
            "cur_mean": round(cur_mean, 3),
            "normalized_shift": round(shift, 3),
            "drifted": shift > threshold,
        }

        if shift > threshold:
            drift_report["drifted_features"].append(col)

    drift_report["has_drift"] = len(drift_report["drifted_features"]) > 0
    return drift_report


def detect_confidence_drop(window: int = 50) -> dict[str, Any]:
    """Check if recent predictions show declining confidence."""
    if not PREDICTIONS_LOG.exists():
        return {"has_drop": False, "message": "No prediction logs yet"}

    df = pd.read_csv(PREDICTIONS_LOG)
    if len(df) < window * 2:
        return {"has_drop": False, "message": "Not enough data for analysis"}

    recent = df.tail(window)["confidence"].mean()
    older = df.iloc[-window*2:-window]["confidence"].mean()

    drop = older - recent
    return {
        "has_drop": drop > 0.1,
        "recent_mean": round(recent, 3),
        "older_mean": round(older, 3),
        "drop": round(drop, 3),
        "message": (
            f"Confidence dropped by {drop:.3f} (older={older:.3f}, recent={recent:.3f})"
            if drop > 0.1
            else "Confidence is stable"
        ),
    }


def get_prediction_stats() -> dict[str, Any]:
    """Summary statistics from prediction logs."""
    if not PREDICTIONS_LOG.exists():
        return {"total_predictions": 0}

    df = pd.read_csv(PREDICTIONS_LOG)
    return {
        "total_predictions": len(df),
        "avg_confidence": round(df["confidence"].mean(), 3) if len(df) > 0 else 0,
        "avg_latency_ms": round(df["latency_ms"].mean(), 1) if len(df) > 0 else 0,
        "low_confidence_pct": round(
            (df["confidence"] < 0.5).mean() * 100, 1
        ) if len(df) > 0 else 0,
        "most_recommended": df["material"].mode().iloc[0] if len(df) > 0 else "N/A",
    }
