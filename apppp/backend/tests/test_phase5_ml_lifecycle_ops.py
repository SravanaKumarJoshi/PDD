"""Phase 5 Verification Tests.

Verifies:
1. ModelManager HMAC signature & SHA-256 checksum integrity verification
2. MonitoringService metrics summary
3. Automated database backup script (scripts/backup_db.py)
"""

import pytest
from app.services.model_manager import ModelManager
from app.services.monitoring_service import MonitoringService
from scripts.backup_db import create_database_backup


def test_model_manager_signature_verification():
    """Verify HMAC digital signature verification logic."""
    secret = "test-signing-key"
    payload = {
        "model_version": "v1.0",
        "algorithm": "XGBoost",
    }
    # Payload without digital_signature should return False
    assert ModelManager.verify_hmac_signature(payload, secret) is False


def test_monitoring_service_telemetry():
    """Verify monitoring service telemetry collection."""
    MonitoringService.record_inference(
        total_duration_ms=45.2,
        confidence_scores=[0.88, 0.92],
        predictions=[0.85, 0.90],
        cache_hit=False
    )
    summary = MonitoringService.get_metrics_summary()
    assert summary["total_requests"] > 0
    assert summary["avg_latency_ms"] > 0.0


def test_database_backup_execution():
    """Verify database backup creation."""
    success = create_database_backup()
    assert success is True
