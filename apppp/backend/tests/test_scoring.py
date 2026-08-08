"""Unit tests for the scoring engine."""

import pytest
from app.scoring.engine import range_overlap_score, inverse_point_score, band_score, score_and_rank
from app.schemas.recommendation import RequirementInput


class TestRangeOverlapScore:
    def test_perfect_overlap(self):
        """Actual range perfectly contains target range."""
        score = range_overlap_score(10, 100, 20, 80)
        assert score == 1.0

    def test_partial_overlap(self):
        """Actual range partially overlaps target."""
        score = range_overlap_score(10, 50, 30, 70)
        assert score is not None
        assert 0 < score < 1
        assert abs(score - 0.5) < 0.01  # 20/40 overlap

    def test_no_overlap(self):
        """Actual range entirely outside target."""
        score = range_overlap_score(100, 200, 10, 50)
        assert score is not None
        assert score < 0.5  # Distance penalty

    def test_none_values(self):
        """Returns None if any value is None."""
        assert range_overlap_score(None, 100, 10, 50) is None
        assert range_overlap_score(10, 100, None, 50) is None
        assert range_overlap_score(10, None, 10, 50) is None

    def test_exact_match(self):
        """Actual range exactly equals target."""
        score = range_overlap_score(30, 100, 30, 100)
        assert score == 1.0


class TestInversePointScore:
    def test_below_target(self):
        """Actual value below target max — perfect score."""
        assert inverse_point_score(50, 100) == 1.0

    def test_equal_target(self):
        """Actual value equals target max — perfect score."""
        assert inverse_point_score(100, 100) == 1.0

    def test_above_target(self):
        """Actual value exceeds target — decaying score."""
        score = inverse_point_score(200, 100)
        assert score == 0.5

    def test_none_values(self):
        assert inverse_point_score(None, 100) is None
        assert inverse_point_score(100, None) is None


class TestBandScore:
    def test_within_budget(self):
        assert band_score("low", "med") == 1.0
        assert band_score("low", "low") == 1.0

    def test_over_budget(self):
        assert band_score("high", "low") == 0.3

    def test_none(self):
        assert band_score(None, "low") is None


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

    def test_basic_scoring(self):
        """A material that matches requirements should score high."""
        req = RequirementInput()  # all defaults
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
                                   tensile_strength_mpa_min=200,
                                   tensile_strength_mpa_max=300)

        result = score_and_rank(req, [good, poor])
        assert len(result.recommendations) == 2
        assert result.recommendations[0].material_name == "Good"

    def test_explanations_generated(self):
        """Recommendations should include explanation factors."""
        req = RequirementInput()
        materials = [self._make_material()]
        result = score_and_rank(req, materials)

        rec = result.recommendations[0]
        assert len(rec.top_factors) > 0
        assert all(f.factor and f.description for f in rec.top_factors)

    def test_empty_materials(self):
        """Empty materials list should return empty recommendations."""
        req = RequirementInput()
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
        """Material with all None properties should still score (with penalties)."""
        req = RequirementInput()
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
        # Should get partial credit for missing data (0.3 per dimension)
        assert 0 < rec.score <= 0.4  # Heavy penalty for all-missing
        assert rec.confidence < 0.5  # Low evidence + zero completeness

    def test_score_bounds(self):
        """All scores should be between 0.0 and 1.0."""
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
            assert 0.0 <= rec.score <= 1.0, f"Score out of bounds: {rec.score}"
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
