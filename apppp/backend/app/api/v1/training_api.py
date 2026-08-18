import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd

_p = Path(__file__).resolve().parent
while _p.parent != _p:
    if (_p / "src").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
    _p = _p.parent

from src.data import load_dataset_auto, FEATURE_COLUMNS
from src.xgboost_model import train_xgboost, get_feature_importance
from src.model import train_model as train_rf, compare_models
from src.evaluation import run_strict_validation
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["Model Training"])

class TrainRequestSchema(BaseModel):
    test_size: float = Field(0.3, ge=0.1, le=0.5, description="Holdout test dataset fraction")
    random_state: int = Field(42, ge=0, description="Random seed")
    cv_folds: int = Field(5, ge=2, le=10, description="Cross validation splits")


@router.post("/train")
async def train_models(payload: TrainRequestSchema):
    """Train XGBoost and RandomForest models and return comparison metrics."""
    try:
        df, stats, source = load_dataset_auto()

        # Train XGBoost
        xgb_model, xgb_metrics = train_xgboost(
            df, test_size=payload.test_size, random_state=payload.random_state, cv_folds=payload.cv_folds
        )

        # Train RandomForest
        rf_model, rf_metrics = train_rf(
            df, test_size=payload.test_size, random_state=payload.random_state, cv_folds=payload.cv_folds
        )

        # Compare
        comparison = compare_models(xgb_metrics, rf_metrics)

        # Feature importances
        importance = get_feature_importance(xgb_model)
        importance_list = [
            {"feature": k, "importance": float(v)}
            for k, v in sorted(importance.items(), key=lambda x: x[1], reverse=True)
        ]

        # Strict validation
        xgb_val = run_strict_validation(
            XGBClassifier,
            {
                "n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
                "subsample": 0.7, "colsample_bytree": 0.7,
                "reg_alpha": 0.1, "reg_lambda": 1.0, "min_child_weight": 3,
                "eval_metric": "logloss", "random_state": payload.random_state
            },
            df, cv_folds=payload.cv_folds, random_state=payload.random_state
        )

        def convert_cm(cm):
            if isinstance(cm, np.ndarray):
                return cm.tolist()
            return cm

        # Format metrics
        xgb_metrics_clean = {
            k: (v.tolist() if isinstance(v, np.ndarray) else float(v) if isinstance(v, (np.floating, float)) else v)
            for k, v in xgb_metrics.items()
        }
        xgb_metrics_clean["confusion_matrix"] = convert_cm(xgb_metrics["confusion_matrix"])

        rf_metrics_clean = {
            k: (v.tolist() if isinstance(v, np.ndarray) else float(v) if isinstance(v, (np.floating, float)) else v)
            for k, v in rf_metrics.items()
        }
        rf_metrics_clean["confusion_matrix"] = convert_cm(rf_metrics["confusion_matrix"])

        holdout_cm = convert_cm(xgb_val["holdout_metrics"]["confusion_matrix"])
        holdout_metrics_clean = {
            "accuracy": float(xgb_val["holdout_metrics"]["accuracy"]),
            "f1": float(xgb_val["holdout_metrics"]["f1"]),
            "roc_auc": float(xgb_val["holdout_metrics"]["roc_auc"]),
            "confusion_matrix": holdout_cm
        }

        return {
            "status": "success",
            "xgboost": xgb_metrics_clean,
            "random_forest": rf_metrics_clean,
            "comparison": comparison,
            "feature_importance": importance_list,
            "validation": {
                "overfit_warning": xgb_val.get("overfit_warning"),
                "holdout_metrics": holdout_metrics_clean,
                "cv_summary": {
                    "accuracy_mean": float(xgb_val["cv_summary"]["accuracy_mean"]),
                    "accuracy_std": float(xgb_val["cv_summary"]["accuracy_std"]),
                },
                "fold_metrics": [
                    {k: float(v) if isinstance(v, (np.floating, float)) else v for k, v in fold.items()}
                    for fold in xgb_val.get("fold_metrics", [])
                ]
            }
        }
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )
