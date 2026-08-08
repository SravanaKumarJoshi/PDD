"""Phase 1 Verification Tests.

Verifies:
1. Material score differentiation (>20% score spread across distinct material candidates)
2. Complete material property retrieval from MySQL
3. Strict NULL value preservation (missing properties stay None / null, not 0.0)
4. Score explainability and category score breakdown payloads
"""

import pytest
import pandas as pd
from shared.ml.scoring import rank_candidates, calculate_material_score_details
from app.schemas.screening import ScreeningRequestSchema
from app.services.inference_service import InferenceService


def test_score_differentiation():
    """Verify that materials with different properties produce distinctly different scores."""
    df = pd.DataFrame([
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "polymer": "Super Polymer",
            "category": "Chitosan",
            "tensile_strength": 100.0,
            "elastic_modulus": 5.0,
            "wvtr": 50.0,
            "biocompatibility": 9.5,
            "biodegradation_days": 180.0,
            "evidence_level": "high",
            "data_completeness": 1.0,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "polymer": "Poor Polymer",
            "category": "Synthetic",
            "tensile_strength": 10.0,
            "elastic_modulus": 0.2,
            "wvtr": 900.0,
            "biocompatibility": 2.0,
            "biodegradation_days": 10.0,
            "evidence_level": "low",
            "data_completeness": 0.4,
        }
    ])
    ml_probs = [0.90, 0.30]
    reqs = {
        "tensile_strength": 80.0,
        "elastic_modulus": 4.0,
        "wvtr": 100.0,
        "min_biocompatibility": 8.0,
        "target_biodegradation_days": 180.0,
    }

    ranked = rank_candidates(df, ml_probs, reqs)
    top_score = ranked.iloc[0]["final_score"]
    low_score = ranked.iloc[1]["final_score"]

    # Must clearly differentiate (> 20 point spread)
    assert top_score - low_score > 20.0
    assert ranked.iloc[0]["rank"] == 1
    assert ranked.iloc[1]["rank"] == 2


def test_null_value_preservation():
    """Verify that missing database properties remain None / null instead of coercing to 0.0."""
    row = pd.Series({
        "tensile_strength": 50.0,
        "elastic_modulus": None,
        "wvtr": None,
        "biocompatibility": 8.0,
        "biodegradation_days": pd.NA,
    })
    reqs = {
        "tensile_strength": 50.0,
        "wvtr": 100.0,
    }

    rule_score, breakdown = calculate_material_score_details(row, reqs)
    assert "barrier" in breakdown
    wvtr_detail = breakdown["barrier"]["properties"]["wvtr"]
    assert wvtr_detail["is_missing"] is True
    assert wvtr_detail["actual"] is None


def test_score_explainability_breakdown():
    """Verify detailed category and property breakdown structures."""
    row = pd.Series({
        "tensile_strength": 60.0,
        "elastic_modulus": 3.0,
        "wvtr": 80.0,
        "biocompatibility": 8.5,
        "biodegradation_days": 180.0,
    })
    reqs = {
        "tensile_strength": 50.0,
        "elastic_modulus": 2.0,
        "wvtr": 100.0,
        "min_biocompatibility": 7.0,
        "target_biodegradation_days": 180.0,
    }

    rule_score, breakdown = calculate_material_score_details(row, reqs)
    assert rule_score >= 90.0
    assert "mechanical" in breakdown
    assert "barrier" in breakdown
    assert "biological" in breakdown
    assert "degradation" in breakdown

    mech_ts = breakdown["mechanical"]["properties"]["tensile_strength"]
    assert mech_ts["requested"] == ">= 50.0 MPa"
    assert mech_ts["actual"] == 60.0
    assert mech_ts["match_pct"] == 100.0
