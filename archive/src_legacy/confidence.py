"""
Confidence & uncertainty modeling with Platt scaling.
Outputs calibrated probabilities and risk categories.
"""
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from typing import Any


RISK_CATEGORIES = {
    "high": {"min": 0.8, "label": "High Confidence", "color": "green"},
    "moderate": {"min": 0.5, "label": "Moderate Confidence", "color": "orange"},
    "low": {"min": 0.0, "label": "Low Confidence — verify experimentally", "color": "red"},
}


def calibrate_model(model, X, y, method="isotonic", random_state=42):
    """
    Calibrate model probabilities using Platt scaling or isotonic regression.
    Returns a CalibratedClassifierCV wrapper.
    """
    X_train, X_cal, y_train, y_cal = train_test_split(
        X, y, test_size=0.3, random_state=random_state, stratify=y
    )
    model.fit(X_train, y_train)
    calibrated = CalibratedClassifierCV(model, method=method, cv="prefit")
    calibrated.fit(X_cal, y_cal)
    return calibrated


def compute_confidence_score(
    calibrated_proba: float,
    evidence_level: str = "med",
    data_completeness: float = 1.0,
) -> float:
    """
    Compute overall confidence from calibrated probability,
    evidence level, and data completeness.
    """
    evidence_map = {"low": 0.4, "med": 0.7, "high": 1.0}
    ev = evidence_map.get(evidence_level, 0.4)
    confidence = 0.5 * calibrated_proba + 0.3 * ev + 0.2 * data_completeness
    return round(min(max(confidence, 0.0), 1.0), 3)


def get_risk_category(confidence: float) -> dict:
    """Return risk category dict for a confidence score."""
    if confidence >= 0.8:
        return RISK_CATEGORIES["high"]
    elif confidence >= 0.5:
        return RISK_CATEGORIES["moderate"]
    else:
        return RISK_CATEGORIES["low"]


def compute_prediction_uncertainty(
    model, X, n_bootstrap: int = 50,
) -> np.ndarray:
    """
    Estimate prediction uncertainty via bootstrap sampling
    of the model's tree estimators (works for RF and XGBoost).
    """
    try:
        # For tree-based models with estimators_
        if hasattr(model, "estimators_"):
            n_est = len(model.estimators_)
            n_samples = min(n_bootstrap, n_est)
            indices = np.random.choice(n_est, size=n_samples, replace=False)
            preds = []
            for i in indices:
                est = model.estimators_[i]
                if hasattr(est, "predict_proba"):
                    preds.append(est.predict_proba(X)[:, 1])
                else:
                    preds.append(est.predict(X).astype(float))
            preds = np.array(preds)
            return preds.std(axis=0)
        else:
            # Fallback: return zeros
            return np.zeros(X.shape[0])
    except Exception:
        return np.zeros(X.shape[0])


def format_confidence_output(
    material_name: str,
    suitability_score: float,
    confidence: float,
    uncertainty: float,
) -> str:
    """Format confidence information as human-readable text."""
    risk = get_risk_category(confidence)
    return (
        f"Material: {material_name}\n"
        f"Suitability Score: {suitability_score:.2f}\n"
        f"Confidence: {confidence:.2f} ({risk['label']})\n"
        f"Uncertainty: ±{uncertainty:.3f}"
    )
