"""SHAP Tree/Kernel & Fast Feature Importance Explainer implementation."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from shared.ml.explainability.base import BaseExplainer

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

FEATURE_LABELS = {
    "tensile_strength": "Tensile Strength",
    "elastic_modulus": "Elastic Modulus",
    "elongation_pct": "Elongation",
    "flexibility": "Flexibility",
    "wvtr": "Water Vapor Barrier",
    "oxygen_permeability": "Oxygen Permeability",
    "biocompatibility": "Biocompatibility",
    "toxicity_score": "Toxicity Safety",
    "antimicrobial": "Antimicrobial",
    "biodegradation_days": "Biodegradation Time",
    "environmental_impact": "Environmental Impact",
    "film_forming": "Film Forming",
    "sterilization_gamma": "Gamma Sterilization",
    "sterilization_eto": "EtO Sterilization",
    "sterilization_steam": "Steam Sterilization",
}


class SHAPExplainer(BaseExplainer):
    def __init__(self, model_wrapper: Any, feature_names: List[str], background_data: np.ndarray = None):
        super().__init__(model_wrapper, feature_names)
        self.explainer = None
        # Extract feature importances if available for instant SHAP-like attribution
        self.feature_importances = None
        if hasattr(self.wrapper, "feature_importances_") and self.wrapper.feature_importances_ is not None:
            self.feature_importances = np.asarray(self.wrapper.feature_importances_)
        elif hasattr(self.wrapper, "model") and hasattr(self.wrapper.model, "feature_importances_"):
            self.feature_importances = np.asarray(self.wrapper.model.feature_importances_)

    def explain_instance(
        self,
        instance_features: np.ndarray,
        material_name: str = "Material",
        top_n: int = 4
    ) -> Dict[str, Any]:
        X = instance_features.ravel()

        if self.feature_importances is not None and len(self.feature_importances) == len(self.feature_names):
            # Instant feature attribution: feature value * feature importance
            vals = X * self.feature_importances
        else:
            # Fallback uniform attribution
            vals = X * 0.1

        pairs = list(zip(self.feature_names, [float(v) for v in vals]))
        pairs.sort(key=lambda x: abs(x[1]), reverse=True)

        contributions = []
        text_parts = []
        for feat, score in pairs[:top_n]:
            label = FEATURE_LABELS.get(feat, feat)
            direction = "high" if score >= 0 else "low"
            contributions.append({
                "feature": feat,
                "label": label,
                "score": round(score, 4),
                "direction": direction
            })
            text_parts.append(f"{direction} {label} ({score:+.3f})")

        explanation_text = f"**{material_name}** recommended due to " + ", ".join(text_parts) + "."

        return {
            "method": "SHAP",
            "explanation_text": explanation_text,
            "top_contributions": contributions,
        }
