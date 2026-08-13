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

from src.data import load_dataset_from_mysql, FEATURE_COLUMNS
from src.explainability import (
    compute_shap_values, generate_explanation_text, FEATURE_LABELS
)
from src.xgboost_model import train_xgboost

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/explainability", tags=["Explainability"])

# Cached trained model for fast explainability response
_CACHED_XGB = None

def get_or_train_xgb(df: pd.DataFrame):
    global _CACHED_XGB
    if _CACHED_XGB is None:
        _CACHED_XGB, _ = train_xgboost(df)
    return _CACHED_XGB


@router.get("/global")
async def get_global_explainability():
    """Retrieve SHAP global feature importances across dataset."""
    try:
        df, stats, error = load_dataset_from_mysql()
        if error:
            raise RuntimeError(error)
        
        model = get_or_train_xgb(df)
        X = df[FEATURE_COLUMNS]

        shap_vals = compute_shap_values(model, X)
        vals = getattr(shap_vals, 'values', np.array(shap_vals))
        if vals.ndim == 3:
            vals = vals[:, :, 1]

        mean_abs_shap = np.abs(vals).mean(axis=0)

        feature_importance = [
            {
                "feature": feat,
                "label": FEATURE_LABELS.get(feat, feat),
                "importance": float(mean_abs_shap[i])
            }
            for i, feat in enumerate(FEATURE_COLUMNS)
        ]
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "features": feature_importance,
            "total_materials": len(df)
        }
    except Exception as e:
        logger.error(f"Global SHAP calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Global SHAP calculation failed: {str(e)}"
        )


@router.get("/material/{polymer_name}")
async def get_material_explanation(polymer_name: str):
    """Retrieve detailed SHAP explanation for a specific material by polymer name."""
    try:
        df, stats, error = load_dataset_from_mysql()
        if error:
            raise RuntimeError(error)

        matching = df[df["polymer"].str.lower() == polymer_name.lower()]
        if matching.empty:
            raise HTTPException(status_code=404, detail=f"Material '{polymer_name}' not found.")

        idx = matching.index[0]
        pos = list(df.index).index(idx)

        model = get_or_train_xgb(df)
        X = df[FEATURE_COLUMNS]

        shap_vals = compute_shap_values(model, X)
        vals = getattr(shap_vals, 'values', np.array(shap_vals))
        if vals.ndim == 3:
            vals = vals[:, :, 1]

        mat_vals = vals[pos]
        text_explanation = generate_explanation_text(mat_vals, FEATURE_COLUMNS, matching.iloc[0]["polymer"])

        contributions = []
        for i, feat in enumerate(FEATURE_COLUMNS):
            contributions.append({
                "feature": feat,
                "label": FEATURE_LABELS.get(feat, feat),
                "shap_value": float(mat_vals[i]),
                "direction": "positive" if mat_vals[i] > 0 else "negative",
                "actual_value": float(X.iloc[pos][feat])
            })
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        return {
            "polymer": matching.iloc[0]["polymer"],
            "explanation_text": text_explanation,
            "contributions": contributions,
            "properties": matching.iloc[0].to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Material SHAP failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Material explanation failed: {str(e)}"
        )


class CompareRequestSchema(BaseModel):
    polymer_a: str
    polymer_b: str


@router.post("/compare")
async def compare_materials_shap(payload: CompareRequestSchema):
    """Compare SHAP values between two materials."""
    try:
        df, stats, error = load_dataset_from_mysql()
        if error:
            raise RuntimeError(error)

        mA = df[df["polymer"].str.lower() == payload.polymer_a.lower()]
        mB = df[df["polymer"].str.lower() == payload.polymer_b.lower()]

        if mA.empty or mB.empty:
            raise HTTPException(status_code=404, detail="One or both materials not found.")

        posA = list(df.index).index(mA.index[0])
        posB = list(df.index).index(mB.index[0])

        model = get_or_train_xgb(df)
        X = df[FEATURE_COLUMNS]

        shap_vals = compute_shap_values(model, X)
        vals = getattr(shap_vals, 'values', np.array(shap_vals))
        if vals.ndim == 3:
            vals = vals[:, :, 1]

        diff = vals[posA] - vals[posB]

        comparisons = []
        for i, feat in enumerate(FEATURE_COLUMNS):
            comparisons.append({
                "feature": feat,
                "label": FEATURE_LABELS.get(feat, feat),
                "shap_a": float(vals[posA][i]),
                "shap_b": float(vals[posB][i]),
                "difference": float(diff[i]),
                "favors": payload.polymer_a if diff[i] > 0 else payload.polymer_b
            })
        comparisons.sort(key=lambda x: abs(x["difference"]), reverse=True)

        return {
            "polymer_a": mA.iloc[0]["polymer"],
            "polymer_b": mB.iloc[0]["polymer"],
            "comparisons": comparisons
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SHAP comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SHAP comparison failed: {str(e)}"
        )
