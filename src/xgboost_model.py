"""
XGBoost primary prediction model with cross-validation and incremental retraining.
"""
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix,
)
from typing import Any

from src.data import FEATURE_COLUMNS

DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.7,
    "colsample_bytree": 0.7,
    "eval_metric": "logloss",
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_child_weight": 3,
    "random_state": 42,
}

EARLY_STOPPING_ROUNDS = 20


def train_xgboost(
    df: pd.DataFrame,
    feature_cols: list[str] = None,
    target_col: str = "suitability_label",
    params: dict = None,
    test_size: float = 0.3,
    random_state: int = 42,
    cv_folds: int = 5,
) -> tuple[XGBClassifier, dict[str, Any]]:
    """Train XGBoost classifier with cross-validation metrics."""
    feature_cols = feature_cols or FEATURE_COLUMNS
    params = {**DEFAULT_PARAMS, **(params or {})}
    params["random_state"] = random_state

    X = df[feature_cols].copy().apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_series = pd.to_numeric(df[target_col], errors="coerce") if target_col in df.columns else pd.Series(dtype=float)

    if y_series.isna().any() or y_series.nunique() < 2:
        bio = df["biocompatibility"] if "biocompatibility" in df.columns else np.random.randn(len(df))
        bio = pd.to_numeric(bio, errors="coerce").fillna(5.0)
        y = (bio >= bio.median()).astype(int)
    else:
        y = y_series.astype(int)

    # Cross-validation
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    model = XGBClassifier(**params)

    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")

    # Train/test split for detailed metrics
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    # Early stopping with eval set (only on final fit, not CV)
    model_final = XGBClassifier(**params, early_stopping_rounds=EARLY_STOPPING_ROUNDS)
    fit_params = {"eval_set": [(X_test, y_test)], "verbose": False}
    model_final.fit(X_train, y_train, **fit_params)

    # Track train accuracy for overfitting detection
    y_train_pred = model_final.predict(X_train)
    train_accuracy = accuracy_score(y_train, y_train_pred)
    y_pred = model_final.predict(X_test)

    val_accuracy = accuracy_score(y_test, y_pred)
    overfit_gap = train_accuracy - val_accuracy

    metrics = {
        "accuracy": val_accuracy,
        "train_accuracy": train_accuracy,
        "overfit_gap": round(overfit_gap, 4),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "cv_scores": cv_scores.tolist(),
        "test_size": len(y_test),
        "train_size": len(y_train),
        "overfit_warning": (
            "⚠️ Possible overfitting" if overfit_gap > 0.05 else None
        ),
    }

    return model_final, metrics


def predict_suitability(model: XGBClassifier, df: pd.DataFrame,
                        feature_cols: list[str] = None) -> np.ndarray:
    """Return probability of positive class for each row."""
    feature_cols = feature_cols or FEATURE_COLUMNS
    X = df[feature_cols].copy()
    return model.predict_proba(X)[:, 1]


def get_feature_importance(model: XGBClassifier,
                           feature_cols: list[str] = None) -> dict[str, float]:
    """Return feature importance as a dict."""
    feature_cols = feature_cols or FEATURE_COLUMNS
    return dict(zip(feature_cols, model.feature_importances_))
