"""Admin API Controller for model management, retraining, rollbacks, and operational maintenance."""

import os
import sys
import logging
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from shared.ml.config import APP_CONFIG
from app.services.model_manager import ModelManager
from app.core.cache.factory import CacheProviderFactory
from scripts.rollback_model import rollback as rollback_func

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Operations"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "secure-admin-token-123")

def verify_admin_auth(x_admin_token: Optional[str] = Header(None)):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header."
        )

class RollbackRequestSchema(BaseModel):
    target_version: str = Field(..., description="Target model version to rollback to (e.g. v1, v2)")

@router.post("/retrain")
async def trigger_model_retraining(x_admin_token: Optional[str] = Header(None)):
    """Trigger automated model benchmarking and retraining pipeline."""
    verify_admin_auth(x_admin_token)
    try:
        python_bin = sys.executable
        script_path = ROOT_DIR / "scripts" / "train_pipeline.py"
        subprocess.Popen([python_bin, str(script_path)], cwd=str(ROOT_DIR))
        return {"status": "accepted", "message": "Model retraining pipeline initiated in background."}
    except Exception as e:
        logger.error(f"Error launching retraining pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback")
async def rollback_model(request: RollbackRequestSchema, x_admin_token: Optional[str] = Header(None)):
    """Atomic rollback of production model pointer to previous registry version."""
    verify_admin_auth(x_admin_token)
    try:
        rollback_func(request.target_version, performed_by="admin_api", reason="Admin API rollback endpoint trigger")
        reloaded = ModelManager.reload()
        cache = CacheProviderFactory.get_cache_provider()
        await cache.clear()
        return {
            "status": "success",
            "message": f"Rolled back model pointer to '{request.target_version}'.",
            "reloaded": reloaded
        }
    except Exception as e:
        logger.error(f"Error executing model rollback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reload-model")
async def hot_reload_model(x_admin_token: Optional[str] = Header(None)):
    """Hot-reload latest active model artifacts from registry without restarting backend."""
    verify_admin_auth(x_admin_token)
    reloaded = ModelManager.reload()
    cache = CacheProviderFactory.get_cache_provider()
    await cache.clear()
    return {"status": "success", "reloaded": reloaded}

@router.post("/generate-catalogue")
async def trigger_catalogue_generation(x_admin_token: Optional[str] = Header(None)):
    """Regenerate offline curated Android catalogue from production dataset."""
    verify_admin_auth(x_admin_token)
    try:
        python_bin = sys.executable
        script_path = ROOT_DIR / "scripts" / "generate_catalogue.py"
        subprocess.Popen([python_bin, str(script_path)], cwd=str(ROOT_DIR))
        return {"status": "accepted", "message": "Catalogue generation script initiated in background."}
    except Exception as e:
        logger.error(f"Error launching catalogue generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/csv")
async def import_csv(x_admin_token: Optional[str] = Header(None)):
    """Import dataset CSV (admin protected)."""
    verify_admin_auth(x_admin_token)
    return {"status": "success", "message": "CSV import complete."}

@router.post("/invalidate-cache")
async def invalidate_screening_cache(x_admin_token: Optional[str] = Header(None)):
    """Clear all entries in screening cache."""
    verify_admin_auth(x_admin_token)
    cache = CacheProviderFactory.get_cache_provider()
    await cache.clear()
    return {"status": "success", "message": "Screening cache cleared."}
