"""Screening History API Controller."""

import logging
from fastapi import APIRouter
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/screening", tags=["Screening"])

@router.get("/history")
async def get_screening_history() -> List[Dict[str, Any]]:
    """Retrieve past screening session history for current user."""
    # Placeholder returning empty session history until DB persistence enabled
    return []
