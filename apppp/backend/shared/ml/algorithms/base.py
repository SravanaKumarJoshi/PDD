"""Base estimator wrapper interface for model-agnostic benchmarking and inference."""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

class BaseEstimatorWrapper(ABC):
    """Abstract interface for all model wrappers."""

    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}
        self.model = None

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the underlying model on feature matrix X and target y."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return probability predictions for the positive class (shape: (N,))."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return binary class predictions (shape: (N,))."""
        pass

    def get_feature_importance(self, feature_names: list[str]) -> Dict[str, float]:
        """Return feature importance as a dictionary if supported."""
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            return dict(zip(feature_names, [float(v) for v in importances]))
        return {f: 0.0 for f in feature_names}
