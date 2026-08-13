"""Confidence and uncertainty estimation."""

from typing import Dict, Any

RISK_CATEGORIES = {
    "high": {"min": 0.8, "label": "High Confidence", "color": "green"},
    "moderate": {"min": 0.5, "label": "Moderate Confidence", "color": "orange"},
    "low": {"min": 0.0, "label": "Low Confidence — verify experimentally", "color": "red"},
}

def compute_confidence_score(
    calibrated_proba: float,
    evidence_level: str = "med",
    data_completeness: float = 1.0,
) -> float:
    """Compute overall composite confidence score."""
    evidence_map = {"low": 0.4, "med": 0.7, "high": 1.0}
    ev = evidence_map.get(evidence_level, 0.4)
    confidence = 0.5 * calibrated_proba + 0.3 * ev + 0.2 * data_completeness
    return round(min(max(confidence, 0.0), 1.0), 3)

def get_risk_category(confidence: float) -> Dict[str, Any]:
    """Return risk category dict for confidence score."""
    if confidence >= 0.8:
        res = dict(RISK_CATEGORIES["high"])
        res["level"] = "high"
    elif confidence >= 0.5:
        res = dict(RISK_CATEGORIES["moderate"])
        res["level"] = "moderate"
    else:
        res = dict(RISK_CATEGORIES["low"])
        res["level"] = "low"
    res.setdefault("reasons", [])
    return res

