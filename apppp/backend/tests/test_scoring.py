"""Unit tests for the scoring engine."""

import pytest
from app.scoring.engine import (
    score_min_requirement,
    score_max_requirement,
    score_range_requirement,
    score_inverse_point,
    score_ordinal_band,
    score_and_rank,
)
from app.schemas.recommendation import RequirementInput


class TestContinuousScoringHelpers:
    def test_score_min_requirement(self):
        """Test continuous minimum requirement scoring."""
        # Below minimum -> continuous decay
        assert score_min_requirement(30, 50) == 42.0
        # At minimum -> 80%
        assert score_min_requirement(50, 50) == 80.0
        # Surplus margin -> scales up to 100%
        assert score_min_requirement(70, 50) == 88.0
        assert score_min_requirement(100, 50) == 100.0
        # Missing value -> 25% penalty
        assert score_min_requirement(None, 50) == 25.0

    def test_score_max_requirement(self):
        """Test continuous maximum requirement scoring."""
        # Under max -> 85% to 100%
        assert score_max_requirement(50, 100) == 92.5
        assert score_max_requirement(100, 100) == 85.0
        # Exceeds max -> continuous inverse ratio decay
        assert score_max_requirement(150, 100) == 56.67
        # Missing value -> 25% penalty
        assert score_max_requirement(None, 100) == 25.0

    def test_score_range_requirement(self):
        """Test range requirement continuous distance scoring."""
        # Target range 2.0 to 4.0 (midpoint 3.0, half 1.0)
        assert score_range_requirement(3.0, 3.0, 2.0, 4.0) == 100.0
        assert score_range_requirement(2.5, 2.5, 2.0, 4.0) == 92.5
        assert score_range_requirement(2.0, 2.0, 2.0, 4.0) == 85.0
        # Outside range -> decay
        assert score_range_requirement(1.0, 1.0, 2.0, 4.0) == 15.0
        assert score_range_requirement(None, None, 2.0, 4.0) == 25.0

    def test_score_ordinal_band(self):
        """Test cost/availability band scoring."""
        assert score_ordinal_band("low", "med", higher_is_better=False) == 100.0
        assert score_ordinal_band("med", "med", higher_is_better=False) == 85.0
        assert score_ordinal_band("high", "med", higher_is_better=False) == 45.0
        assert score_ordinal_band(None, "med") == 25.0


class TestScoreAndRank:
    """Integration test for the full scoring pipeline."""

    def _make_material(self, name="Test Material", category="chitosan", **overrides):
        props = {
            "tensile_strength_mpa_min": 30,
            "tensile_strength_mpa_max": 100,
            "elastic_modulus_gpa_min": 1.0,
            "elastic_modulus_gpa_max": 4.0,
            "elongation_pct_min": 5,
            "elongation_pct_max": 30,
            "puncture_resistance_n": 15,
            "wvtr": 180,
            "otr": 95,
            "degradation_days_min": 30,
            "degradation_days_max": 180,
            "cytotoxicity_safe": True,
            "hemocompatible": True,
            "antimicrobial": True,
            "ster_gamma": True,
            "ster_eto": True,
            "ster_steam": False,
            "ster_uv": True,
            "ster_autoclave": False,
            "proc_film": True,
            "proc_casting": True,
            "proc_extrusion": False,
            "proc_coating": True,
            "proc_melt": False,
            "cost_band": "low",
            "availability_band": "high",
            "data_completeness": 0.85,
        }
        props.update(overrides)
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": name,
            "category": category,
            "evidence_level": "med",
            "properties": props,
        }

    def test_empty_criteria_returns_no_recommendations(self):
        """When no screening criteria are provided, empty recommendations should be returned."""
        req = RequirementInput()  # all defaults (empty criteria)
        materials = [self._make_material()]
        result = score_and_rank(req, materials)
        assert len(result.recommendations) == 0

    def test_basic_scoring(self):
        """A material that matches requirements should score high."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        materials = [self._make_material()]
        result = score_and_rank(req, materials)

        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.score > 0
        assert rec.confidence > 0
        assert rec.material_name == "Test Material"

    def test_hard_constraint_filters(self):
        """Materials failing hard constraints should be filtered out."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        req.sterilization.steam_required = True  # Material has ster_steam=False
        materials = [self._make_material()]
        result = score_and_rank(req, materials)

        assert len(result.recommendations) == 0
        assert result.materials_filtered_out == 1

    def test_ranking_order(self):
        """Better-matching material should rank higher."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 30
        req.mechanical.tensile_strength_max = 100

        good = self._make_material(name="Good",
                                   tensile_strength_mpa_min=30,
                                   tensile_strength_mpa_max=100)
        poor = self._make_material(name="Poor",
                                   tensile_strength_mpa_min=5,
                                   tensile_strength_mpa_max=10)

        result = score_and_rank(req, [good, poor])
        assert len(result.recommendations) == 2
        assert result.recommendations[0].material_name == "Good"

    def test_explanations_generated(self):
        """Recommendations should include explanation factors."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        materials = [self._make_material()]
        result = score_and_rank(req, materials)

        rec = result.recommendations[0]
        assert len(rec.top_factors) > 0
        assert all(f.factor and f.description for f in rec.top_factors)

    def test_empty_materials(self):
        """Empty materials list should return empty recommendations."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        result = score_and_rank(req, [])
        assert len(result.recommendations) == 0

    def test_determinism_100_runs(self):
        """Same inputs must produce identical outputs across 100 runs."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 20
        req.mechanical.tensile_strength_max = 80
        materials = [
            self._make_material(name=f"Mat{i}", tensile_strength_mpa_min=10 + i * 5,
                                tensile_strength_mpa_max=50 + i * 10)
            for i in range(10)
        ]

        first_result = score_and_rank(req, materials)
        first_scores = [(r.material_name, r.score) for r in first_result.recommendations]

        for _ in range(99):
            result = score_and_rank(req, materials)
            scores = [(r.material_name, r.score) for r in result.recommendations]
            assert scores == first_scores, "Scoring is not deterministic"

    def test_tie_stability(self):
        """Materials with identical properties should produce identical scores
        and maintain stable insertion-order sort."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        mat_a = self._make_material(name="Alpha")
        mat_b = self._make_material(name="Beta")
        # Same properties → same scores
        mat_b["id"] = "00000000-0000-0000-0000-000000000002"

        result = score_and_rank(req, [mat_a, mat_b])
        assert len(result.recommendations) == 2
        # Scores should be equal
        assert result.recommendations[0].score == result.recommendations[1].score
        # Stable sort: first-in stays first
        assert result.recommendations[0].material_name == "Alpha"
        assert result.recommendations[1].material_name == "Beta"

    def test_response_schema_snapshot(self):
        """Verify response contains all expected keys and types."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        materials = [self._make_material()]
        result = score_and_rank(req, materials)

        # Top-level response fields
        assert hasattr(result, "recommendations")
        assert hasattr(result, "scoring_version")
        assert hasattr(result, "total_materials_evaluated")
        assert hasattr(result, "materials_filtered_out")
        assert isinstance(result.scoring_version, str)
        assert isinstance(result.total_materials_evaluated, int)

        # Recommendation fields
        rec = result.recommendations[0]
        assert hasattr(rec, "material_id")
        assert hasattr(rec, "material_name")
        assert hasattr(rec, "category")
        assert hasattr(rec, "score")
        assert hasattr(rec, "confidence")
        assert hasattr(rec, "top_factors")
        assert hasattr(rec, "concerns")
        assert hasattr(rec, "unmet_constraints")
        assert hasattr(rec, "tradeoffs")
        assert isinstance(rec.score, float)
        assert isinstance(rec.confidence, float)
        assert isinstance(rec.top_factors, list)
        assert isinstance(rec.tradeoffs, list)

        # Factor contribution fields
        if rec.top_factors:
            f = rec.top_factors[0]
            assert hasattr(f, "factor")
            assert hasattr(f, "score")
            assert hasattr(f, "description")
            assert isinstance(f.factor, str)
            assert isinstance(f.score, float)

    def test_all_null_properties(self):
        """Material with all None properties should score 25.0 (penalty) for requested criteria."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 10.0
        mat = {
            "id": "00000000-0000-0000-0000-000000000099",
            "name": "Empty Material",
            "category": "unknown",
            "evidence_level": "low",
            "properties": {},
        }
        result = score_and_rank(req, [mat])
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.score == 25.0

    def test_score_bounds(self):
        """All scores should be between 0.0 and 100.0."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 1
        req.mechanical.tensile_strength_max = 500
        req.barrier.wvtr_max = 500
        req.barrier.otr_max = 500

        materials = [
            self._make_material(name="Perfect",
                                tensile_strength_mpa_min=1,
                                tensile_strength_mpa_max=500,
                                wvtr=10, otr=10),
            self._make_material(name="Poor",
                                tensile_strength_mpa_min=500,
                                tensile_strength_mpa_max=1000,
                                wvtr=5000, otr=5000),
        ]
        result = score_and_rank(req, materials)
        for rec in result.recommendations:
            assert 0.0 <= rec.score <= 100.0, f"Score out of bounds: {rec.score}"
            assert 0.0 <= rec.confidence <= 1.0, f"Confidence out of bounds: {rec.confidence}"

    def test_fully_specified_requirements(self):
        """Engine should handle requirements where every field is set."""
        req = RequirementInput()
        req.mechanical.tensile_strength_min = 20
        req.mechanical.tensile_strength_max = 100
        req.mechanical.elastic_modulus_min = 0.5
        req.mechanical.elastic_modulus_max = 5.0
        req.mechanical.elongation_min = 5
        req.mechanical.elongation_max = 50
        req.mechanical.puncture_resistance_min = 10
        req.barrier.wvtr_max = 200
        req.barrier.otr_max = 100
        req.degradation.degradation_days_min = 30
        req.degradation.degradation_days_max = 180
        req.degradation.hydrolytic_stability_min = "med"
        req.cost.max_cost_band = "med"
        req.cost.min_availability_band = "med"
        req.biological.cytotoxicity_safe_required = True
        req.biological.hemocompatible_required = True

        materials = [self._make_material()]
        result = score_and_rank(req, materials)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].score > 0
