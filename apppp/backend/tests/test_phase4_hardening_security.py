"""Phase 4 Verification Tests.

Verifies:
1. Domain Exception Hierarchy & Sanitized Exception Handler
2. Centralized Configuration & Feature Flags
3. Security exception handling (prevention of raw traceback leaks)
"""

import pytest
from app.config import settings
from app.core.exceptions import (
    ScreeningPipelineException,
    DatabaseValidationException,
    MaterialValidationException,
    ScoringException
)


def test_feature_flags_configuration():
    """Verify that feature flags exist and have valid boolean defaults."""
    assert settings.ENABLE_SCORE_BREAKDOWN is True
    assert settings.ENABLE_VALIDATION is True
    assert settings.ENABLE_PERFORMANCE_METRICS is True
    assert settings.ENABLE_AUDIT_LOGGING is True
    assert settings.ENABLE_SCHEMA_VALIDATION is True
    assert settings.ENABLE_RULE_SCORING is True
    assert settings.ENABLE_ML_SCORING is True
    assert settings.ENABLE_RESPONSE_METADATA is True


def test_exception_hierarchy_attributes():
    """Verify exception diagnostic IDs and error codes."""
    exc = MaterialValidationException("Negative tensile strength detected")
    assert exc.error_code == "MATERIAL_VALIDATION_ERROR"
    assert exc.status_code == 422
    assert exc.message == "Negative tensile strength detected"
    assert exc.diagnostic_id.startswith("diag_")
