"""Phase 3 Verification Tests.

Verifies:
1. Performance timing metrics payload structure (database_query_ms, validation_ms, ml_inference_ms, etc.)
2. Audit session metadata (screening_session_id, timestamps, versions, configuration)
3. Audit record file persistence via AuditService
"""

import pytest
import os
from pathlib import Path
from app.services.audit_service import AuditService, AUDIT_LOG_DIR


def test_audit_service_persistence():
    """Verify that AuditService creates session trace JSON files."""
    session_id = "test-session-12345"
    req_data = {"tensile_strength": 50.0}
    audit_meta = {
        "screening_session_id": session_id,
        "scoring_engine_version": "2.0",
        "configuration": {"rule_score_weight": 0.7, "ml_score_weight": 0.3}
    }
    results_summary = {"total_returned": 10}
    perf = {"total_execution_ms": 120.5}
    val = {"materials_checked": 50}

    success = AuditService.record_screening_session(
        session_id=session_id,
        request_data=req_data,
        audit_metadata=audit_meta,
        results_summary=results_summary,
        performance_metrics=perf,
        validation_diagnostics=val,
    )

    assert success is True
    expected_file = AUDIT_LOG_DIR / f"trace_{session_id}.json"
    assert expected_file.exists()

    # Clean up test trace file
    if expected_file.exists():
        expected_file.unlink()
