"""
RandomForest benchmarking model and ensemble prediction.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix,
)
from typing import Any

from src.data import FEATURE_COLUMNS


def prepare_features(df: pd.DataFrame,
                     feature_cols: list[str] = None) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare features and labels for training."""
    feature_cols = feature_cols or FEATURE_COLUMNS
    X = df[feature_cols].copy()
    y = df["suitability_label"].copy()
    if y.nunique() < 2:
        bio = df["biocompatibility"] if "biocompatibility" in df.columns else np.random.randn(len(df))
        y = (bio >= bio.median()).astype(int)
    return X, y


def train_model(
    df: pd.DataFrame,
    test_size: float = 0.3,
    random_state: int = 42,
    cv_folds: int = 5,
) -> tuple[RandomForestClassifier, dict[str, Any]]:
    """Train RandomForest with cross-validation metrics."""
    X, y = prepare_features(df)

    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    model = RandomForestClassifier(
        n_estimators=100, max_depth=5,
        random_state=random_state, class_weight="balanced",
    )
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "cv_scores": cv_scores.tolist(),
        "test_size": len(y_test),
        "train_size": len(y_train),
    }
    return model, metrics


def predict_suitability(model, df: pd.DataFrame,
                        feature_cols: list[str] = None) -> np.ndarray:
    """Return probability of positive class."""
    feature_cols = feature_cols or FEATURE_COLUMNS
    X = df[feature_cols].copy()
    return model.predict_proba(X)[:, 1]


def compare_models(xgb_metrics: dict, rf_metrics: dict) -> dict:
    """Side-by-side comparison of XGBoost vs RandomForest."""
    keys = ["accuracy", "precision", "recall", "f1", "cv_mean", "cv_std"]
    comparison = {}
    for k in keys:
        comparison[k] = {
            "xgboost": xgb_metrics.get(k, 0),
            "random_forest": rf_metrics.get(k, 0),
            "winner": "xgboost" if xgb_metrics.get(k, 0) >= rf_metrics.get(k, 0) else "random_forest",
        }
    return comparison


def ensemble_predict(
    xgb_proba: np.ndarray,
    rf_proba: np.ndarray,
    weights: tuple[float, float] = (0.7, 0.3),
) -> np.ndarray:
    """Weighted ensemble of XGBoost and RandomForest probabilities."""
    return weights[0] * xgb_proba + weights[1] * rf_proba
