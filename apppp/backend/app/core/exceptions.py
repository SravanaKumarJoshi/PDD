"""Domain Exception Hierarchy & Standardized Error Handling."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ScreeningPipelineException(Exception):
    """Base exception class for screening pipeline domain errors."""
    error_code = "SCREENING_PIPELINE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, diagnostic_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.diagnostic_id = diagnostic_id or f"diag_{uuid.uuid4().hex[:8]}"


class DatabaseValidationException(ScreeningPipelineException):
    error_code = "DATABASE_VALIDATION_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class SchemaValidationException(ScreeningPipelineException):
    error_code = "SCHEMA_VALIDATION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class MaterialValidationException(ScreeningPipelineException):
    error_code = "MATERIAL_VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class ScoringException(ScreeningPipelineException):
    error_code = "SCORING_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ModelInferenceException(ScreeningPipelineException):
    error_code = "MODEL_INFERENCE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class SerializationException(ScreeningPipelineException):
    error_code = "SERIALIZATION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


async def screening_exception_handler(request: Request, exc: ScreeningPipelineException) -> JSONResponse:
    """Standardized error handler preventing raw traceback leaks to public API clients."""
    logger.error(
        f"Pipeline Exception [{exc.error_code}] (diag: {exc.diagnostic_id}): {exc.message}",
        exc_info=True
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "diagnostic_id": exc.diagnostic_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "screening_session_id": getattr(request.state, "request_id", None),
        }
    )
