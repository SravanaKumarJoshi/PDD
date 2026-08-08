"""Model Metadata and Info REST API Controller."""

import logging
from fastapi import APIRouter
from typing import Dict, Any
from app.services.model_manager import ModelManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/model", tags=["Model Info"])

@router.get("/info")
async def get_active_model_info() -> Dict[str, Any]:
    """Retrieve current production model version, algorithm, evaluation metrics, and training timestamp."""
    model_wrapper, scaler, metadata, _ = ModelManager.get_model()

    return {
        "model_version": metadata.get("model_version", "v1"),
        "model_type": metadata.get("model_type", "Baseline Suitability Model (Policy Approximation)"),
        "label_source": metadata.get("label_source", "Rule-Based Threshold Policy"),
        "label_version": metadata.get("label_version", "v1.0"),
        "algorithm": metadata.get("algorithm", getattr(model_wrapper, "name", model_wrapper.__class__.__name__) if model_wrapper else "unknown"),
        "git_commit_hash": metadata.get("git_commit_hash", "untracked"),
        "dataset_hash": metadata.get("dataset_hash", "prod_v1"),
        "governance": metadata.get("governance", {
            "is_empirical_lab_data": False,
            "policy_approximation_note": "Trained on rule-derived baseline suitability policy. Transition to lab outcome labels scheduled for Phase 2."
        }),
        "metrics": metadata.get("selected_metrics", {}),
        "leaderboard": metadata.get("leaderboard", []),
        "trained_at": metadata.get("trained_at", "unknown"),
        "dataset_metadata": metadata.get("dataset_metadata", {}),
    }
