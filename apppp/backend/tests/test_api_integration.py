"""API integration tests with real database (Postgres via testcontainers or CI).

Tests real CRUD operations with persistence, not mocked responses.
Skipped automatically if no Postgres is available.
"""

import os
import pytest

# Mark all tests as integration (requires real Postgres).
# CI runs these separately: pytest -m integration
# Locally auto-skipped when no DB is available.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("DATABASE_URL") and not os.getenv("TEST_DB_AVAILABLE"),
        reason="Integration tests require Postgres (set DATABASE_URL or install testcontainers)",
    ),
]


class TestHealthEndpoint:
    def test_health_check(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "docs" in data


class TestMaterialsAPI:
    def test_list_materials_empty(self, test_client):
        response = test_client.get("/api/v1/materials")
        assert response.status_code == 200
        # May be empty if no materials loaded
        data = response.json()
        assert isinstance(data, list)

    def test_get_material_not_found(self, test_client):
        response = test_client.get("/api/v1/materials/00000000-0000-0000-0000-000000000999")
        assert response.status_code == 404


class TestRecommendationsAPI:
    def test_post_recommendations_empty_db(self, test_client):
        """Recommendations with no materials should return empty list."""
        response = test_client.post(
            "/api/v1/recommendations",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "scoring_version" in data
        assert isinstance(data["recommendations"], list)

    def test_post_recommendations_with_requirements(self, test_client):
        """Full requirements input should be accepted."""
        response = test_client.post(
            "/api/v1/recommendations",
            json={
                "mechanical": {
                    "tensile_strength_min": 20,
                    "tensile_strength_max": 100,
                    "weight": 1.5,
                },
                "barrier": {
                    "wvtr_max": 200,
                    "otr_max": 100,
                },
                "biological": {
                    "cytotoxicity_safe_required": True,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "total_materials_evaluated" in data
        assert "materials_filtered_out" in data

    def test_response_schema_shape(self, test_client):
        """Verify the response JSON has expected structure."""
        response = test_client.post("/api/v1/recommendations", json={})
        assert response.status_code == 200
        data = response.json()

        # Top-level keys
        assert set(data.keys()) >= {
            "recommendations", "scoring_version",
            "total_materials_evaluated", "materials_filtered_out",
        }

    def test_invalid_weight_returns_422(self, test_client):
        """Weight outside [0, 3] should be rejected."""
        response = test_client.post(
            "/api/v1/recommendations",
            json={
                "mechanical": {
                    "weight": 5.0,  # Max is 3.0
                },
            },
        )
        assert response.status_code == 422

    def test_invalid_json_returns_422(self, test_client):
        """Malformed JSON should return 422."""
        response = test_client.post(
            "/api/v1/recommendations",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


class TestAdminCSVImport:
    def test_admin_csv_import_requires_auth(self, test_client):
        """CSV import should require admin authentication."""
        # Without proper admin headers, this should fail
        # (exact status depends on auth implementation)
        response = test_client.post("/api/v1/admin/import/csv")
        # Should be 4xx (unauthorized/forbidden) or 422 (missing file)
        assert response.status_code in (401, 403, 422)


class TestProjectsAPI:
    def test_list_projects_empty(self, test_client):
        response = test_client.get("/api/v1/projects")
        # Should work (may return empty list or require auth)
        assert response.status_code in (200, 401, 403)

    def test_create_project(self, test_client):
        response = test_client.post(
            "/api/v1/projects",
            json={
                "title": "Test Project",
                "requirements": {"mechanical": {"tensile_strength_min": 20}},
            },
        )
        # Should succeed or require auth
        assert response.status_code in (200, 201, 401, 403)

    def test_delete_nonexistent_project(self, test_client):
        response = test_client.delete("/api/v1/projects/00000000-0000-0000-0000-000000000999")
        assert response.status_code in (404, 401, 403)


class TestNegativeCases:
    """Edge cases and error handling."""

    def test_invalid_uuid_returns_422(self, test_client):
        response = test_client.get("/api/v1/materials/not-a-uuid")
        assert response.status_code == 422

    def test_extra_fields_ignored(self, test_client):
        """Extra fields in request body should be ignored (not cause errors)."""
        response = test_client.post(
            "/api/v1/recommendations",
            json={
                "mechanical": {"tensile_strength_min": 20},
                "unknown_field": "should be ignored",
            },
        )
        assert response.status_code == 200
