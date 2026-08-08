"""Screening API Controller."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.screening import ScreeningRequestSchema, ScreeningResponseSchema
from app.services.inference_service import InferenceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screening", tags=["Screening"])


@router.post("", response_model=ScreeningResponseSchema)
@router.post("/", response_model=ScreeningResponseSchema, include_in_schema=False)
async def screen_materials(
    request: ScreeningRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> ScreeningResponseSchema:
    """Execute AI screening pipeline for candidate biopolymers."""
    try:
        return await InferenceService.execute_screening(request, db=db)
    except Exception as e:
        logger.error(f"Error executing screening request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screening pipeline execution failed: {str(e)}"
        )
