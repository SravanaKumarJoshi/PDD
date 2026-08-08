"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.ops import router as ops_router
from app.api.v1.screening import router as screening_router
from app.api.v1.screening_explain import router as screening_explain_router
from app.api.v1.screening_history import router as screening_history_router
from app.api.v1.materials import router as materials_router
from app.api.v1.materials_stream import router as materials_stream_router
from app.api.v1.statistics import router as statistics_router
from app.api.v1.model_info import router as model_info_router
from app.api.v1.projects import router as projects_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")

# Operational & System endpoints
api_router.include_router(ops_router)

# AI Screening endpoints
api_router.include_router(screening_router)
api_router.include_router(screening_explain_router)
api_router.include_router(screening_history_router)

# Materials Catalog & Streaming Sync endpoints
api_router.include_router(materials_stream_router)
api_router.include_router(materials_router)

# System & Metadata endpoints
api_router.include_router(statistics_router)
api_router.include_router(model_info_router)

# Projects & User workspace
api_router.include_router(projects_router)

# Administration
api_router.include_router(admin_router)
