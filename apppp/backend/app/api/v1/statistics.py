"""Statistics REST API Controller."""

import logging
from fastapi import APIRouter
from typing import Dict, Any
from shared.ml.config import FEATURE_COLUMNS, MATERIAL_TABLE_NAME
from scripts.train_pipeline import load_data_from_mysql_or_fallback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/statistics", tags=["Statistics"])

@router.get("")
async def get_dataset_statistics() -> Dict[str, Any]:
    """Get production dataset summary statistics, category distributions, and feature counts."""
    df = load_data_from_mysql_or_fallback()
    cat_counts = df["category"].value_counts().to_dict() if "category" in df.columns else {}

    return {
        "table_name": MATERIAL_TABLE_NAME,
        "total_materials": len(df),
        "total_features": len(FEATURE_COLUMNS),
        "categories": cat_counts,
        "feature_list": FEATURE_COLUMNS,
    }
