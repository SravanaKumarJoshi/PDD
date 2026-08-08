"""SVM and linear algorithm wrappers."""

import numpy as np
from typing import Dict, Any
from sklearn.svm import SVC
from shared.ml.algorithms.base import BaseEstimatorWrapper

class SVMWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {"probability": True, "random_state": 42}
        default_params.update(params or {})
        super().__init__("SupportVectorMachine", default_params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = SVC(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)
