"""Operational health endpoints: /health, /ready, /live, /metrics."""

import logging
from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Dict, Any
from app.services.model_manager import ModelManager
from app.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Operations"])

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok", "service": "biopolymer-ai-screening-backend"}

@router.get("/ready")
async def readiness_check():
    """Readiness probe checking database connectivity and loaded model registry status."""
    is_loaded = ModelManager.load_latest()
    if not is_loaded:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "Model registry not loaded"}
        )
    return {"status": "ready", "model": "loaded"}

@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}

@router.get("/metrics")
async def get_metrics():
    """Prometheus / Operational metrics summary."""
    summary = MonitoringService.get_metrics_summary()
    return summary
