"""Model-agnostic evaluation, GroupKFold leakage prevention, calibration, and automated algorithm selection."""

import time
import sys
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss
)
from sklearn.model_selection import GroupKFold
from sklearn.calibration import CalibratedClassifierCV

from shared.ml.algorithms.tree_models import (
    XGBoostWrapper, LightGBMWrapper, CatBoostWrapper,
    RandomForestWrapper, ExtraTreesWrapper, GradientBoostingWrapper
)
from shared.ml.algorithms.linear_models import SVMWrapper
from shared.ml.config import TRAINING_CONFIG

ALGORITHM_REGISTRY = {
    "xgboost": XGBoostWrapper,
    "lightgbm": LightGBMWrapper,
    "catboost": CatBoostWrapper,
    "random_forest": RandomForestWrapper,
    "extra_trees": ExtraTreesWrapper,
    "gradient_boosting": GradientBoostingWrapper,
    "svm": SVMWrapper,
}

def evaluate_algorithm_with_group_cv(
    wrapper,
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups_train: np.ndarray,
    X_holdout: np.ndarray,
    y_holdout: np.ndarray,
    cv_folds: int = 5,
) -> Dict[str, Any]:
    """Fit model with Platt scaling probability calibration and GroupKFold cross-validation."""
    start_train = time.perf_counter()

    # Fit base wrapper
    wrapper.fit(X_train, y_train)

    # Wrap with Platt Scaling Probability Calibration
    calibrated_model = None
    try:
        if hasattr(wrapper, "model") and wrapper.model is not None:
            calibrated_model = CalibratedClassifierCV(wrapper.model, method="sigmoid", cv="prefit")
            calibrated_model.fit(X_train, y_train)
    except Exception:
        calibrated_model = None

    train_duration_ms = (time.perf_counter() - start_train) * 1000.0

    # Latency benchmark
    start_inf = time.perf_counter()
    for _ in range(100):
        if calibrated_model is not None:
            y_proba = calibrated_model.predict_proba(X_holdout)[:, 1]
        else:
            y_proba = wrapper.predict_proba(X_holdout)
    avg_latency_ms = ((time.perf_counter() - start_inf) * 1000.0) / 100.0

    if calibrated_model is not None:
        y_pred = (calibrated_model.predict_proba(X_holdout)[:, 1] >= 0.5).astype(int)
    else:
        y_pred = wrapper.predict(X_holdout)

    acc = float(accuracy_score(y_holdout, y_pred))
    prec = float(precision_score(y_holdout, y_pred, zero_division=0))
    rec = float(recall_score(y_holdout, y_pred, zero_division=0))
    f1 = float(f1_score(y_holdout, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_holdout, y_proba))
    except Exception:
        auc = 0.5

    # GroupKFold Cross Validation (groups by polymer name to prevent data leakage)
    cv_scores = []
    try:
        gkf = GroupKFold(n_splits=min(cv_folds, len(np.unique(groups_train))))
        for train_idx, val_idx in gkf.split(X_train, y_train, groups=groups_train):
            X_tr, y_tr = X_train[train_idx], y_train[train_idx]
            X_va, y_va = X_train[val_idx], y_train[val_idx]

            sub_wrapper = wrapper.__class__(wrapper.params)
            sub_wrapper.fit(X_tr, y_tr)
            p_val = sub_wrapper.predict(X_va)
            cv_scores.append(f1_score(y_va, p_val, zero_division=0))

        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    except Exception:
        cv_mean = f1
        cv_std = 0.0

    return {
        "algorithm": wrapper.name,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "group_cv_f1_mean": round(cv_mean, 4),
        "group_cv_f1_std": round(cv_std, 4),
        "platt_calibrated": calibrated_model is not None,
        "train_time_ms": round(train_duration_ms, 2),
        "inference_latency_ms": round(avg_latency_ms, 3),
    }

def benchmark_and_select_best_model_leakage_free(
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups_train: np.ndarray,
    X_holdout: np.ndarray,
    y_holdout: np.ndarray,
    config: Dict[str, Any] = None,
) -> Tuple[Any, Dict[str, Any], List[Dict[str, Any]]]:
    """GroupKFold leakage-free model benchmarking and selection."""
    config = config or TRAINING_CONFIG
    algo_configs = config.get("algorithms", {})
    metric_weights = config.get("metric_weights", {"f1": 0.35, "accuracy": 0.25, "precision": 0.15, "recall": 0.15, "cv_mean": 0.10})

    results = []
    trained_wrappers = {}

    for key, wrapper_cls in ALGORITHM_REGISTRY.items():
        algo_cfg = algo_configs.get(key, {})
        if algo_cfg.get("enabled", True):
            try:
                params = algo_cfg.get("params", {})
                wrapper = wrapper_cls(params)
                metrics = evaluate_algorithm_with_group_cv(
                    wrapper, X_train, y_train, groups_train, X_holdout, y_holdout
                )

                comp_score = (
                    metrics["f1"] * metric_weights.get("f1", 0.35) +
                    metrics["accuracy"] * metric_weights.get("accuracy", 0.25) +
                    metrics["precision"] * metric_weights.get("precision", 0.15) +
                    metrics["recall"] * metric_weights.get("recall", 0.15) +
                    metrics["group_cv_f1_mean"] * metric_weights.get("cv_mean", 0.10)
                )
                metrics["composite_score"] = round(comp_score, 4)

                results.append(metrics)
                trained_wrappers[wrapper.name] = wrapper
            except Exception as e:
                print(f"Skipping candidate algorithm '{key}': {e}", file=sys.stderr)

    if not results:
        raise RuntimeError("No candidate algorithms successfully trained.")

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    best_metrics = results[0]
    best_wrapper = trained_wrappers[best_metrics["algorithm"]]

    return best_wrapper, best_metrics, results
