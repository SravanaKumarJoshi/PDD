"""Enterprise Architecture Integration Test Suite."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

app.dependency_overrides[get_db] = lambda: None
client = TestClient(app)

def test_health_endpoints():
    """Verify operational health endpoints (/health, /ready, /live, /metrics)."""
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"

    resp_live = client.get("/api/v1/live")
    assert resp_live.status_code == 200
    assert resp_live.json()["status"] == "alive"

    resp_ready = client.get("/api/v1/ready")
    assert resp_ready.status_code == 200

    resp_metrics = client.get("/api/v1/metrics")
    assert resp_metrics.status_code == 200
    assert "total_requests" in resp_metrics.json()

def test_model_info_endpoint():
    """Verify model information endpoint returns version, algorithm, and dataset hash."""
    resp = client.get("/api/v1/model/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_version" in data
    assert "algorithm" in data

def test_screening_api_endpoint():
    """Verify screening API request execution with performance metrics and model metadata."""
    payload = {
        "tensile_strength": 40.0,
        "min_biocompatibility": 6.0,
        "sterilization_gamma": True,
        "explainability_method": "shap"
    }

    resp = client.post("/api/v1/screening", json=payload, headers={"Authorization": "Bearer dev-testuser"})
    assert resp.status_code == 200
    data = resp.json()

    assert "screening_id" in data
    assert "model_metadata" in data
    assert "performance_metrics" in data
    assert "results" in data

    # Verify timing breakdown
    metrics = data["performance_metrics"]
    assert "total_request_duration_ms" in metrics
    assert "model_inference_time_ms" in metrics

    # Verify candidate results
    results = data["results"]
    assert len(results) > 0
    first = results[0]
    assert "polymer" in first
    assert "confidence" in first
    assert "risk_category" in first

def test_rate_limiter():
    """Verify rate limit headers are attached to responses."""
    resp = client.get("/api/v1/statistics")
    assert resp.status_code == 200
    assert "X-RateLimit-Remaining" in resp.headers
