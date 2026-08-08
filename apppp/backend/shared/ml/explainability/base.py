"""Abstract base interface for model explainability modules."""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from typing import Dict, Any, List

class BaseExplainer(ABC):
    """Abstract interface for pluggable explainability providers (SHAP, LIME, etc.)."""

    def __init__(self, model_wrapper: Any, feature_names: List[str]):
        self.wrapper = model_wrapper
        self.feature_names = feature_names

    @abstractmethod
    def explain_instance(
        self,
        instance_features: np.ndarray,
        material_name: str = "Material",
        top_n: int = 4
    ) -> Dict[str, Any]:
        """Generate feature contributions and human-readable text for a single material instance."""
        pass
