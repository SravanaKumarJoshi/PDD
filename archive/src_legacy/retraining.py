"""
Validated real-time learning pipeline with human-in-the-loop approval.
"""
import json
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
from typing import Any

MODEL_STORE = Path(__file__).parent.parent / "model_store"
FEEDBACK_DIR = Path(__file__).parent.parent / "feedback"
VERSIONS_FILE = MODEL_STORE / "versions.json"
MAX_VERSIONS = 5

VALID_ROLES = {"doctor", "researcher", "admin", "engineer"}


def _ensure_dirs():
    MODEL_STORE.mkdir(exist_ok=True)
    FEEDBACK_DIR.mkdir(exist_ok=True)


def validate_feedback(entry: dict) -> tuple[bool, str]:
    """
    Validate feedback before accepting.
    Returns (is_valid, reason).
    """
    role = entry.get("user_role", "").lower()
    if role not in VALID_ROLES:
        return False, f"Invalid role: {role}. Must be one of {VALID_ROLES}"

    rating = entry.get("rating")
    if rating is None or not (1 <= rating <= 10):
        return False, "Rating must be between 1 and 10"

    if not entry.get("material_name"):
        return False, "Material name is required"

    confidence = entry.get("self_confidence", 3)
    if confidence < 3:
        return False, "LOW_CONFIDENCE"  # Goes to pending review

    return True, "OK"


def submit_feedback(entry: dict) -> str:
    """
    Submit feedback through validation layer.
    Returns: 'approved', 'pending_review', or 'rejected'.
    """
    _ensure_dirs()
    entry["timestamp"] = datetime.now().isoformat()

    is_valid, reason = validate_feedback(entry)

    if reason == "LOW_CONFIDENCE":
        _append_csv(FEEDBACK_DIR / "pending_review.csv", entry)
        return "pending_review"
    elif not is_valid:
        entry["rejection_reason"] = reason
        _append_csv(FEEDBACK_DIR / "rejected_feedback.csv", entry)
        return "rejected"
    else:
        _append_csv(FEEDBACK_DIR / "approved_feedback.csv", entry)
        return "approved"


def approve_pending(index: int) -> bool:
    """Admin approves a pending feedback entry."""
    _ensure_dirs()
    pending_path = FEEDBACK_DIR / "pending_review.csv"
    if not pending_path.exists():
        return False

    df = pd.read_csv(pending_path)
    if index >= len(df):
        return False

    row = df.iloc[index].to_dict()
    _append_csv(FEEDBACK_DIR / "approved_feedback.csv", row)
    df = df.drop(index).reset_index(drop=True)
    df.to_csv(pending_path, index=False)
    return True


def get_approved_count() -> int:
    """Count approved feedback entries."""
    path = FEEDBACK_DIR / "approved_feedback.csv"
    if not path.exists():
        return 0
    return len(pd.read_csv(path))


def should_retrain(threshold: int = 20) -> bool:
    """Check if enough approved feedback to warrant retraining."""
    return get_approved_count() >= threshold


def save_model_version(model, model_type: str, metrics: dict):
    """Save model with version tracking."""
    _ensure_dirs()

    versions = _load_versions()
    version_num = len(versions) + 1
    tag = f"v{version_num}"

    filename = f"{tag}_{model_type}.joblib"
    joblib.dump(model, MODEL_STORE / filename)

    versions.append({
        "version": tag,
        "model_type": model_type,
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "metrics": {k: v for k, v in metrics.items()
                    if k not in ("confusion_matrix",)},
    })

    # Cleanup old versions
    if len(versions) > MAX_VERSIONS:
        for old in versions[:-MAX_VERSIONS]:
            old_file = MODEL_STORE / old["filename"]
            if old_file.exists():
                old_file.unlink()
        versions = versions[-MAX_VERSIONS:]

    _save_versions(versions)
    return tag


def load_latest_model(model_type: str = "xgboost"):
    """Load the latest model version."""
    versions = _load_versions()
    for v in reversed(versions):
        if v["model_type"] == model_type:
            path = MODEL_STORE / v["filename"]
            if path.exists():
                return joblib.load(path), v
    return None, None


def get_model_history() -> list[dict]:
    """Return all model versions with metrics."""
    return _load_versions()


def validate_new_model(new_metrics: dict, old_metrics: dict,
                       max_degradation: float = 0.05) -> tuple[bool, str]:
    """Check that new model isn't worse than old by more than threshold."""
    if not old_metrics:
        return True, "No previous model to compare"

    old_acc = old_metrics.get("accuracy", 0)
    new_acc = new_metrics.get("accuracy", 0)

    if new_acc < old_acc - max_degradation:
        return False, (
            f"New model accuracy ({new_acc:.3f}) dropped >5% "
            f"from old ({old_acc:.3f}). Retraining rejected."
        )
    return True, "Model validation passed"


def _append_csv(path: Path, row: dict):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        df.to_csv(path, index=False)


def _load_versions() -> list:
    if VERSIONS_FILE.exists():
        with open(VERSIONS_FILE) as f:
            return json.load(f)
    return []


def _save_versions(versions: list):
    with open(VERSIONS_FILE, 'w') as f:
        json.dump(versions, f, indent=2, default=str)
