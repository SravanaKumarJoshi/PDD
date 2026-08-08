"""Step 0: Baseline Regression Suite.

Captures baseline behavior, sample requests, and current response shapes
before executing Phase 1 through Phase 5.
"""

import pytest
import pandas as pd
from app.schemas.recommendation import RequirementInput, MechanicalRequirements, BarrierRequirements
from app.scoring.engine import score_and_rank
from shared.ml.scoring import rank_candidates


def test_baseline_score_and_rank_structure():
    """Verify baseline output structure from app.scoring.engine."""
    req = RequirementInput(
        mechanical=MechanicalRequirements(tensile_strength_min=20.0, tensile_strength_max=80.0, weight=2.0),
        barrier=BarrierRequirements(wvtr_max=300.0, weight=1.0)
    )
    materials = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Chitosan High Purity",
            "category": "Chitosan",
            "evidence_level": "high",
            "properties": {
                "tensile_strength_mpa_min": 30.0,
                "tensile_strength_mpa_max": 90.0,
                "wvtr": 150.0,
                "data_completeness": 0.95
            }
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Alginate Standard",
            "category": "Alginate",
            "evidence_level": "med",
            "properties": {
                "tensile_strength_mpa_min": 10.0,
                "tensile_strength_mpa_max": 40.0,
                "wvtr": 400.0,
                "data_completeness": 0.80
            }
        }
    ]

    res = score_and_rank(req, materials)
    assert hasattr(res, "recommendations")
    assert len(res.recommendations) == 2
    assert res.recommendations[0].score >= 0.0


def test_baseline_rank_candidates_structure():
    """Verify baseline rank_candidates output shape from shared.ml.scoring."""
    df = pd.DataFrame([
        {"id": "11111111-1111-1111-1111-111111111111", "polymer": "Chitosan", "tensile_strength": 50.0, "wvtr": 150.0},
        {"id": "22222222-2222-2222-2222-222222222222", "polymer": "Alginate", "tensile_strength": 20.0, "wvtr": 400.0}
    ])
    ml_probs = [0.85, 0.65]
    reqs = {"tensile_strength": 40.0, "wvtr": 200.0}

    ranked = rank_candidates(df, ml_probs, reqs)
    assert "ml_probability" in ranked.columns
    assert "final_score" in ranked.columns
    assert len(ranked) == 2
