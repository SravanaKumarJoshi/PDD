"""Security regression tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)

def test_admin_import_rejected_no_token():
    """Admin import must be rejected if no ADMIN_TOKEN is provided."""
    # Assuming CSV import endpoint is /api/v1/admin/import/csv
    response = client.post("/api/v1/admin/import/csv")
    assert response.status_code in (401, 403, 422)  # Should fail, typically 403 or 422 for no file
    
    # Try with dummy file but no token
    response = client.post(
        "/api/v1/admin/import/csv",
        files={"file": ("dummy.csv", b"id,name\n1,test", "text/csv")}
    )
    assert "admin" in response.json().get("detail", "").lower()

def test_dev_token_rejected_in_production(monkeypatch):
    """Dev tokens must be rejected when APP_ENV is not development."""
    # Mock settings.APP_ENV to 'production'
    monkeypatch.setattr(settings, "APP_ENV", "production")
    
    # Send a dev token to a protected endpoint. 
    # For a protected endpoint we might test an admin endpoint or any user-protected endpoint.
    # We will just test the token validation logic via dependency injection if possible, 
    # or just use a dummy protected route if one exists.
    
    # Let's test by directly calling the get_current_user_id function with a mocked Header
    from app.auth.dependencies import get_current_user_id
    from fastapi import HTTPException
    import asyncio
    
    async def run_test():
        try:
            await get_current_user_id(authorization="Bearer dev-12345")
            pytest.fail("Should have raised HTTPException")
        except HTTPException as e:
            assert e.status_code == 401
            assert e.detail == "Authentication failed"
            
    asyncio.run(run_test())
