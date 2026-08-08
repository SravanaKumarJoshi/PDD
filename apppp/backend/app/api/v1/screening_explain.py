"""Screening Explain API Controller."""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from shared.ml.config import FEATURE_COLUMNS
from shared.ml.explainability.factory import ExplainerFactory
from app.services.model_manager import ModelManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/screening", tags=["Screening"])

class ExplainRequestSchema(BaseModel):
    material_name: str = Field(..., description="Name of the material to explain")
    method: str = Field("shap", description="Explainability strategy: shap or lime")
    features: Dict[str, float] = Field(..., description="Map of feature names to float values")

@router.post("/explain")
async def explain_material(request: ExplainRequestSchema):
    """Generate detailed feature-level explanation for a single material."""
    try:
        model_wrapper, scaler, metadata, feature_matrix = ModelManager.get_model()
        explainer = ExplainerFactory.create_explainer(
            request.method, model_wrapper, FEATURE_COLUMNS, background_data=feature_matrix
        )

        import numpy as np
        row_feat = np.array([[request.features.get(c, 0.0) for c in FEATURE_COLUMNS]], dtype=np.float32)
        row_scaled = scaler.transform(row_feat)[0]

        explanation = explainer.explain_instance(
            row_scaled, material_name=request.material_name, top_n=6
        )

        return {
            "material_name": request.material_name,
            "explanation": explanation,
            "model_version": metadata.get("model_version", "v1"),
        }
    except Exception as e:
        logger.error(f"Error generating explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation generation failed: {str(e)}"
        )
