"""Explainer factory to select explainability strategy dynamically."""

from typing import Any, List
from shared.ml.explainability.base import BaseExplainer
from shared.ml.explainability.shap_explainer import SHAPExplainer
from shared.ml.explainability.lime_explainer import LIMEExplainer

class ExplainerFactory:
    """Factory pattern for instantiating explainability strategy."""

    @staticmethod
    def create_explainer(
        method: str,
        model_wrapper: Any,
        feature_names: List[str],
        background_data: Any = None,
    ) -> BaseExplainer:
        method_clean = (method or "shap").lower().strip()
        if method_clean == "lime":
            return LIMEExplainer(model_wrapper, feature_names, background_data)
        else:
            # Default to SHAP
            return SHAPExplainer(model_wrapper, feature_names, background_data)
