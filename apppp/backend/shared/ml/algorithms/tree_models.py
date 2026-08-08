"""Tree-based algorithm wrappers: XGBoost, LightGBM, CatBoost, RandomForest, ExtraTrees, GradientBoosting."""

import numpy as np
from typing import Dict, Any
from shared.ml.algorithms.base import BaseEstimatorWrapper

# Conditional imports with fallback
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except Exception:
    HAS_LIGHTGBM = False

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except Exception:
    HAS_CATBOOST = False

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier

class XGBoostWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("XGBoost", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost library is not installed.")
        self.model = XGBClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


class LightGBMWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("LightGBM", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if not HAS_LIGHTGBM:
            raise RuntimeError("LightGBM library is not installed.")
        self.model = LGBMClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


class CatBoostWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("CatBoost", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if not HAS_CATBOOST:
            raise RuntimeError("CatBoost library is not installed.")
        self.model = CatBoostClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


class RandomForestWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("RandomForest", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = RandomForestClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


class ExtraTreesWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("ExtraTrees", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = ExtraTreesClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


class GradientBoostingWrapper(BaseEstimatorWrapper):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__("GradientBoosting", params)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = GradientBoostingClassifier(**self.params)
        self.model.fit(X, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)
