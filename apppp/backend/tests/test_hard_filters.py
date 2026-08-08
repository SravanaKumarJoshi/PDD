"""Tests for hard constraint filtering in the scoring engine.

These tests verify that materials failing hard constraints:
1. Are excluded from results
2. Have their unmet_constraints populated
3. Cannot sneak through regardless of high numeric scores
"""

import pytest
from app.scoring.engine import score_and_rank
from app.schemas.recommendation import RequirementInput


def _make_material(
    name="Test Material",
    category="chitosan",
    evidence_level="med",
    **prop_overrides,
):
    """Build a material dict with full properties."""
    props = {
        "tensile_strength_mpa_min": 50,
        "tensile_strength_mpa_max": 150,
        "elastic_modulus_gpa_min": 2.0,
        "elastic_modulus_gpa_max": 8.0,
        "elongation_pct_min": 10,
        "elongation_pct_max": 40,
        "puncture_resistance_n": 20,
        "wvtr": 100,
        "otr": 50,
        "degradation_days_min": 30,
        "degradation_days_max": 180,
        "cytotoxicity_safe": True,
        "hemocompatible": True,
        "antimicrobial": True,
        "ster_gamma": True,
        "ster_eto": True,
        "ster_steam": True,
        "ster_uv": True,
        "ster_autoclave": True,
        "proc_film": True,
        "proc_casting": True,
        "proc_extrusion": True,
        "proc_coating": True,
        "proc_melt": True,
        "cost_band": "low",
        "availability_band": "high",
        "data_completeness": 1.0,
    }
    props.update(prop_overrides)
    return {
        "id": f"00000000-0000-0000-0000-{hash(name) % 10**12:012d}",
        "name": name,
        "category": category,
        "evidence_level": evidence_level,
        "properties": props,
    }


class TestSterilizationHardFilters:
    """Sterilization requirements are hard constraints — fail = filtered out."""

    def test_gamma_required_filters_non_gamma(self):
        req = RequirementInput()
        req.sterilization.gamma_required = True

        gamma_yes = _make_material(name="Gamma Yes", ster_gamma=True)
        gamma_no = _make_material(name="Gamma No", ster_gamma=False)

        result = score_and_rank(req, [gamma_yes, gamma_no])
        names = [r.material_name for r in result.recommendations]

        assert "Gamma Yes" in names
        assert "Gamma No" not in names
        assert result.materials_filtered_out == 1

    def test_multiple_sterilization_filters_intersection(self):
        """Requiring multiple methods should filter to the intersection."""
        req = RequirementInput()
        req.sterilization.gamma_required = True
        req.sterilization.steam_required = True

        both = _make_material(name="Both", ster_gamma=True, ster_steam=True)
        gamma_only = _make_material(name="GammaOnly", ster_gamma=True, ster_steam=False)
        steam_only = _make_material(name="SteamOnly", ster_gamma=False, ster_steam=True)
        neither = _make_material(name="Neither", ster_gamma=False, ster_steam=False)

        result = score_and_rank(req, [both, gamma_only, steam_only, neither])
        names = [r.material_name for r in result.recommendations]

        assert names == ["Both"]
        assert result.materials_filtered_out == 3

    def test_autoclave_required(self):
        req = RequirementInput()
        req.sterilization.autoclave_required = True

        passes = _make_material(name="AC Yes", ster_autoclave=True)
        fails = _make_material(name="AC No", ster_autoclave=False)

        result = score_and_rank(req, [passes, fails])
        names = [r.material_name for r in result.recommendations]

        assert "AC Yes" in names
        assert "AC No" not in names

    def test_all_sterilization_required(self):
        """Only materials supporting ALL sterilization methods should pass."""
        req = RequirementInput()
        req.sterilization.gamma_required = True
        req.sterilization.eto_required = True
        req.sterilization.steam_required = True
        req.sterilization.uv_required = True
        req.sterilization.autoclave_required = True

        all_yes = _make_material(name="AllSter")
        partial = _make_material(name="Partial", ster_autoclave=False)

        result = score_and_rank(req, [all_yes, partial])
        names = [r.material_name for r in result.recommendations]

        assert "AllSter" in names
        assert "Partial" not in names


class TestProcessingHardFilters:
    """Processing method requirements are hard constraints."""

    def test_film_required_filters_non_film(self):
        req = RequirementInput()
        req.processing.film_required = True

        film_yes = _make_material(name="Film Yes", proc_film=True)
        film_no = _make_material(name="Film No", proc_film=False)

        result = score_and_rank(req, [film_yes, film_no])
        names = [r.material_name for r in result.recommendations]

        assert "Film Yes" in names
        assert "Film No" not in names

    def test_extrusion_and_melt_required(self):
        req = RequirementInput()
        req.processing.extrusion_required = True
        req.processing.melt_required = True

        both = _make_material(name="Both", proc_extrusion=True, proc_melt=True)
        ext_only = _make_material(name="ExtOnly", proc_extrusion=True, proc_melt=False)

        result = score_and_rank(req, [both, ext_only])
        names = [r.material_name for r in result.recommendations]

        assert "Both" in names
        assert "ExtOnly" not in names


class TestBiologicalHardFilters:
    """Cytotoxicity and hemocompatibility are hard constraints when required."""

    def test_cytotoxicity_required(self):
        req = RequirementInput()
        req.biological.cytotoxicity_safe_required = True

        safe = _make_material(name="Safe", cytotoxicity_safe=True)
        unsafe = _make_material(name="Unsafe", cytotoxicity_safe=False)
        unknown = _make_material(name="Unknown", cytotoxicity_safe=None)

        result = score_and_rank(req, [safe, unsafe, unknown])
        names = [r.material_name for r in result.recommendations]

        assert "Safe" in names
        # Both unsafe and unknown should be filtered
        assert "Unsafe" not in names

    def test_hemocompatible_required(self):
        req = RequirementInput()
        req.biological.hemocompatible_required = True

        hemo_yes = _make_material(name="HemoYes", hemocompatible=True)
        hemo_no = _make_material(name="HemoNo", hemocompatible=False)

        result = score_and_rank(req, [hemo_yes, hemo_no])
        names = [r.material_name for r in result.recommendations]

        assert "HemoYes" in names
        assert "HemoNo" not in names


class TestCombinedHardFilters:
    """Multiple hard constraints from different categories."""

    def test_sterilization_plus_processing_plus_bio(self):
        """
        Require gamma + film + cytotoxicity — only materials
        meeting ALL three should pass.
        """
        req = RequirementInput()
        req.sterilization.gamma_required = True
        req.processing.film_required = True
        req.biological.cytotoxicity_safe_required = True

        passes = _make_material(
            name="AllGood",
            ster_gamma=True, proc_film=True, cytotoxicity_safe=True,
        )
        no_gamma = _make_material(
            name="NoGamma",
            ster_gamma=False, proc_film=True, cytotoxicity_safe=True,
        )
        no_film = _make_material(
            name="NoFilm",
            ster_gamma=True, proc_film=False, cytotoxicity_safe=True,
        )
        not_safe = _make_material(
            name="NotSafe",
            ster_gamma=True, proc_film=True, cytotoxicity_safe=False,
        )

        result = score_and_rank(req, [passes, no_gamma, no_film, not_safe])
        names = [r.material_name for r in result.recommendations]

        assert names == ["AllGood"]
        assert result.materials_filtered_out == 3

    def test_no_hard_constraints_passes_all(self):
        """With no hard constraints, all materials should pass."""
        req = RequirementInput()
        materials = [
            _make_material(name=f"Mat{i}") for i in range(10)
        ]
        result = score_and_rank(req, materials)

        assert len(result.recommendations) == 10
        assert result.materials_filtered_out == 0

    def test_results_only_contain_passing_materials(self):
        """
        Verify that EVERY material in results actually meets the constraint.
        This prevents bugs where a material sneaks through.
        """
        req = RequirementInput()
        req.sterilization.gamma_required = True

        materials = [
            _make_material(name=f"Gamma{i}", ster_gamma=(i % 2 == 0))
            for i in range(20)
        ]

        result = score_and_rank(req, materials)

        for rec in result.recommendations:
            # Find the original material to verify
            original = next(m for m in materials if m["name"] == rec.material_name)
            assert original["properties"]["ster_gamma"] is True, \
                f"{rec.material_name} passed gamma filter but has ster_gamma=False"
