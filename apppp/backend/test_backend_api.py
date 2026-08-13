"""Backend API integration test script for all 3 requirements."""

import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=== 1. TESTING AUTHENTICATION ENFORCEMENT ON SCREENING ===")
        payload = {
            "tensile_strength": 40.0,
            "elastic_modulus": 2.0,
            "elongation_pct": 15.0,
            "wvtr": 100.0,
            "oxygen_permeability": 50.0,
            "min_biocompatibility": 5.0,
            "target_biodegradation_days": 90.0,
            "sterilization_gamma": True,
            "explainability_method": "shap"
        }

        # Unauthenticated request -> expect 401
        resp_unauth = await client.post("/api/v1/screening", json=payload)
        print(f"Unauthenticated POST /api/v1/screening status: {resp_unauth.status_code}")
        assert resp_unauth.status_code == 401
        print("SUCCESS: Unauthenticated screening request correctly rejected with 401\n")

        # Authenticated request -> expect 200
        auth_headers = {"Authorization": "Bearer dev-user1"}
        resp_auth = await client.post("/api/v1/screening", json=payload, headers=auth_headers)
        print(f"Authenticated POST /api/v1/screening status: {resp_auth.status_code}")
        assert resp_auth.status_code == 200
        screening_data = resp_auth.json()
        assert "screening_id" in screening_data
        results = screening_data.get("results", [])
        assert len(results) >= 3
        print(f"SUCCESS: Authenticated screening returned {len(results)} materials\n")

        print("=== 2. TESTING MATERIAL DETAILS FOR 3 DIFFERENT MATERIALS ===")
        mat_a = results[0]
        mat_b = results[1]
        mat_c = results[2]

        print(f"Material A: ID='{mat_a['material_id']}', Polymer='{mat_a['polymer']}'")
        print(f"Material B: ID='{mat_b['material_id']}', Polymer='{mat_b['polymer']}'")
        print(f"Material C: ID='{mat_c['material_id']}', Polymer='{mat_c['polymer']}'")

        # Fetch details A
        resp_a = await client.get(f"/api/v1/materials/{mat_a['material_id']}")
        print(f"GET Details A status: {resp_a.status_code}")
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a.get("id") == mat_a["material_id"] or data_a.get("polymer") == mat_a["polymer"] or data_a.get("name") == mat_a["polymer"]
        print("SUCCESS: Details A matches Material A\n")

        # Fetch details B
        resp_b = await client.get(f"/api/v1/materials/{mat_b['material_id']}")
        print(f"GET Details B status: {resp_b.status_code}")
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        assert data_b.get("id") == mat_b["material_id"] or data_b.get("polymer") == mat_b["polymer"] or data_b.get("name") == mat_b["polymer"]
        print("SUCCESS: Details B matches Material B\n")

        # Fetch details C
        resp_c = await client.get(f"/api/v1/materials/{mat_c['material_id']}")
        print(f"GET Details C status: {resp_c.status_code}")
        assert resp_c.status_code == 200
        data_c = resp_c.json()
        assert data_c.get("id") == mat_c["material_id"] or data_c.get("polymer") == mat_c["polymer"] or data_c.get("name") == mat_c["polymer"]
        print("SUCCESS: Details C matches Material C\n")

        # Nonexistent material -> 404
        resp_404 = await client.get("/api/v1/materials/nonexistent_id_999999")
        print(f"GET Nonexistent Material status: {resp_404.status_code}")
        assert resp_404.status_code == 404
        print("SUCCESS: Nonexistent material returns 404\n")

        print("=== 3. TESTING PREVENT DUPLICATE PROJECT NAMES ===")
        user_a_headers = {"Authorization": "Bearer dev-userA"}
        user_b_headers = {"Authorization": "Bearer dev-userB"}

        proj_payload_1 = {
            "title": "Project Alpha",
            "requirements": {"ts": 40},
            "results": {"count": 5}
        }

        # 1. User A saves "Project Alpha" -> expect 201
        res_save1 = await client.post("/api/v1/projects", json=proj_payload_1, headers=user_a_headers)
        print(f"User A First Save 'Project Alpha' status: {res_save1.status_code}")
        assert res_save1.status_code == 201

        # 2. User A saves "Project Alpha" again -> expect 409 Conflict
        res_save2 = await client.post("/api/v1/projects", json=proj_payload_1, headers=user_a_headers)
        print(f"User A Second Save 'Project Alpha' status: {res_save2.status_code}, Detail: {res_save2.json().get('detail')}")
        assert res_save2.status_code == 409
        assert "already exists" in res_save2.json().get("detail", "").lower()

        # 3. User A saves " Project Alpha " -> expect 409 Conflict
        proj_payload_spaces = {"title": "  Project Alpha  ", "requirements": {}, "results": {}}
        res_save3 = await client.post("/api/v1/projects", json=proj_payload_spaces, headers=user_a_headers)
        print(f"User A Save '  Project Alpha  ' status: {res_save3.status_code}")
        assert res_save3.status_code == 409

        # 4. User A saves "project alpha" -> expect 409 Conflict
        proj_payload_lower = {"title": "project alpha", "requirements": {}, "results": {}}
        res_save4 = await client.post("/api/v1/projects", json=proj_payload_lower, headers=user_a_headers)
        print(f"User A Save 'project alpha' status: {res_save4.status_code}")
        assert res_save4.status_code == 409

        # 5. User B saves "Project Alpha" -> expect 201 Created (per-user uniqueness)
        res_save_user_b = await client.post("/api/v1/projects", json=proj_payload_1, headers=user_b_headers)
        print(f"User B Save 'Project Alpha' status: {res_save_user_b.status_code}")
        assert res_save_user_b.status_code == 201

        print("SUCCESS: Duplicate project name prevention verified!\n")

if __name__ == "__main__":
    print("=== Running BioPolymer Backend API Verification ===\n")
    asyncio.run(main())
    print("ALL BACKEND API TESTS PASSED SUCCESSFULLY!")
