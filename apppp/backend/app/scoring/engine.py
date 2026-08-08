"""Transparent weighted scoring engine for biopolymer recommendations.

Implements a 6-phase pipeline:
1. Hard constraint filtering
2. Numeric range scoring
3. Boolean/categorical scoring
4. Weighted aggregation
5. Confidence computation
6. Explanation generation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from app.schemas.recommendation import (
    RequirementInput,
    RecommendationResult,
    RecommendationResponse,
    FactorContribution,
)
from app.config import settings


@dataclass
class ScoredMaterial:
    material_id: str
    material_name: str
    category: str
    evidence_level: str
    data_completeness: float
    dimension_scores: dict[str, float | None] = field(default_factory=dict)
    hard_failures: list[str] = field(default_factory=list)
    total_score: float = 0.0
    confidence: float = 0.0


# ─── Helper Functions ──────────────────────────────────────────────

def range_overlap_score(
    actual_min: float | None, actual_max: float | None,
    target_min: float | None, target_max: float | None,
) -> float | None:
    """Score 0.0–1.0 based on how well actual range overlaps target range."""
    if actual_min is None or actual_max is None:
        return None
    if target_min is None or target_max is None:
        return None
    if target_max <= target_min:
        return None

    overlap_start = max(actual_min, target_min)
    overlap_end = min(actual_max, target_max)

    if overlap_start > overlap_end:
        # No overlap — compute distance-based penalty
        gap = min(abs(actual_min - target_max), abs(actual_max - target_min))
        target_span = target_max - target_min
        return max(0.0, 1.0 - (gap / target_span))

    overlap_length = overlap_end - overlap_start
    target_length = target_max - target_min
    return min(overlap_length / target_length, 1.0)


def inverse_point_score(actual_value: float | None, target_max: float | None) -> float | None:
    """For properties where lower is better (WVTR, OTR).
    Returns 1.0 if actual <= target, decays toward 0 otherwise."""
    if actual_value is None or target_max is None:
        return None
    if target_max <= 0:
        return None
    if actual_value <= target_max:
        return 1.0
    return min(target_max / actual_value, 1.0)


def band_score(actual_band: str | None, target_max_band: str | None) -> float | None:
    """Score cost/availability bands. Lower cost = better for cost; higher = better for availability."""
    if actual_band is None or target_max_band is None:
        return None
    band_order = {"low": 1, "med": 2, "high": 3}
    actual_val = band_order.get(actual_band.lower(), 2)
    target_val = band_order.get(target_max_band.lower(), 3)
    if actual_val <= target_val:
        return 1.0
    return 0.3  # exceeds budget but not zero


HYDROLYTIC_ORDER = {"low": 1, "med": 2, "high": 3}


# ─── Main Scoring Function ────────────────────────────────────────

def score_and_rank(
    requirements: RequirementInput,
    materials: list[dict],
) -> RecommendationResponse:
    """Run the full scoring pipeline on a list of materials.

    Args:
        requirements: User's requirement input with weights.
        materials: List of dicts with material + properties data.

    Returns:
        RecommendationResponse with ranked results.
    """
    scored: list[ScoredMaterial] = []
    filtered_count = 0

    for mat in materials:
        props = mat.get("properties") or {}
        sm = ScoredMaterial(
            material_id=str(mat["id"]),
            material_name=mat["name"],
            category=mat["category"],
            evidence_level=mat.get("evidence_level", "low"),
            data_completeness=props.get("data_completeness", 0.0) or 0.0,
        )

        # ── PHASE 1: Hard Constraint Filtering ────────────────
        req_s = requirements.sterilization
        if req_s.gamma_required and not props.get("ster_gamma"):
            sm.hard_failures.append("Does not support gamma sterilization")
        if req_s.eto_required and not props.get("ster_eto"):
            sm.hard_failures.append("Does not support EtO sterilization")
        if req_s.steam_required and not props.get("ster_steam"):
            sm.hard_failures.append("Does not support steam sterilization")
        if req_s.uv_required and not props.get("ster_uv"):
            sm.hard_failures.append("Does not support UV sterilization")
        if req_s.autoclave_required and not props.get("ster_autoclave"):
            sm.hard_failures.append("Does not support autoclave sterilization")

        req_p = requirements.processing
        if req_p.film_required and not props.get("proc_film"):
            sm.hard_failures.append("Cannot be processed as film")
        if req_p.casting_required and not props.get("proc_casting"):
            sm.hard_failures.append("Does not support casting")
        if req_p.extrusion_required and not props.get("proc_extrusion"):
            sm.hard_failures.append("Does not support extrusion")
        if req_p.coating_required and not props.get("proc_coating"):
            sm.hard_failures.append("Does not support coating")
        if req_p.melt_required and not props.get("proc_melt"):
            sm.hard_failures.append("Does not support melt processing")

        req_b = requirements.biological
        if req_b.cytotoxicity_safe_required and not props.get("cytotoxicity_safe"):
            sm.hard_failures.append("Does not meet cytotoxicity safety requirement")
        if req_b.hemocompatible_required and not props.get("hemocompatible"):
            sm.hard_failures.append("Does not meet hemocompatibility requirement")

        if sm.hard_failures:
            filtered_count += 1
            continue

        # ── PHASE 2: Numeric Range Scoring ────────────────────
        req_m = requirements.mechanical
        sm.dimension_scores["tensile_strength"] = range_overlap_score(
            props.get("tensile_strength_mpa_min"), props.get("tensile_strength_mpa_max"),
            req_m.tensile_strength_min, req_m.tensile_strength_max,
        )
        sm.dimension_scores["elastic_modulus"] = range_overlap_score(
            props.get("elastic_modulus_gpa_min"), props.get("elastic_modulus_gpa_max"),
            req_m.elastic_modulus_min, req_m.elastic_modulus_max,
        )
        sm.dimension_scores["elongation"] = range_overlap_score(
            props.get("elongation_pct_min"), props.get("elongation_pct_max"),
            req_m.elongation_min, req_m.elongation_max,
        )
        sm.dimension_scores["puncture_resistance"] = (
            inverse_point_score(props.get("puncture_resistance_n"), req_m.puncture_resistance_min)
            if req_m.puncture_resistance_min else None
        )

        req_bar = requirements.barrier
        sm.dimension_scores["wvtr"] = inverse_point_score(
            props.get("wvtr"), req_bar.wvtr_max
        )
        sm.dimension_scores["otr"] = inverse_point_score(
            props.get("otr"), req_bar.otr_max
        )

        req_d = requirements.degradation
        sm.dimension_scores["degradation"] = range_overlap_score(
            props.get("degradation_days_min"), props.get("degradation_days_max"),
            req_d.degradation_days_min, req_d.degradation_days_max,
        )

        # Hydrolytic stability
        if req_d.hydrolytic_stability_min and props.get("hydrolytic_stability"):
            req_level = HYDROLYTIC_ORDER.get(req_d.hydrolytic_stability_min.lower(), 1)
            actual_level = HYDROLYTIC_ORDER.get(props["hydrolytic_stability"].lower(), 1)
            sm.dimension_scores["hydrolytic_stability"] = 1.0 if actual_level >= req_level else 0.3
        else:
            sm.dimension_scores["hydrolytic_stability"] = None

        # ── PHASE 3: Boolean/Categorical Scoring ──────────────
        # Biocompatibility (those not hard-filtered still get scored)
        bio_scores = []
        if props.get("cytotoxicity_safe"):
            bio_scores.append(1.0)
        elif props.get("cytotoxicity_safe") is False:
            bio_scores.append(0.2)

        if props.get("hemocompatible"):
            bio_scores.append(1.0)
        elif props.get("hemocompatible") is False:
            bio_scores.append(0.3)

        if req_b.antimicrobial_required:
            bio_scores.append(1.0 if props.get("antimicrobial") else 0.0)

        sm.dimension_scores["biocompatibility"] = (
            sum(bio_scores) / len(bio_scores) if bio_scores else None
        )

        # Cost
        req_c = requirements.cost
        sm.dimension_scores["cost"] = band_score(
            props.get("cost_band"), req_c.max_cost_band
        )
        sm.dimension_scores["availability"] = (
            band_score(
                # For availability, higher is better — invert the logic
                props.get("availability_band"),
                req_c.min_availability_band,
            )
            if req_c.min_availability_band else None
        )

        # ── PHASE 4: Weighted Aggregation ─────────────────────
        weight_map = {
            "tensile_strength": req_m.weight,
            "elastic_modulus": req_m.weight,
            "elongation": req_m.weight,
            "puncture_resistance": req_m.weight,
            "wvtr": req_bar.weight,
            "otr": req_bar.weight,
            "biocompatibility": req_b.weight,
            "degradation": req_d.weight,
            "hydrolytic_stability": req_d.weight,
            "cost": req_c.weight,
            "availability": req_c.weight,
        }

        total_weighted = 0.0
        total_weight = 0.0
        missing_penalty_count = 0

        for dim, score in sm.dimension_scores.items():
            w = weight_map.get(dim, 1.0)
            if score is not None:
                total_weighted += w * score
                total_weight += w

        sm.total_score = total_weighted / total_weight if total_weight > 0 else 0.3

        # ── PHASE 5: Confidence ───────────────────────────────
        evidence_map = {"low": 0.4, "med": 0.7, "high": 1.0}
        ev_score = evidence_map.get(sm.evidence_level, 0.4)
        sm.confidence = round(
            0.6 * sm.data_completeness + 0.4 * ev_score, 3
        )

        scored.append(sm)

    # ── PHASE 6: Explanation Generation & Rank ────────────────
    results: list[RecommendationResult] = []
    scored.sort(key=lambda x: x.total_score, reverse=True)

    for sm in scored:
        # Build factor contributions
        contributions = []
        for dim, score in sm.dimension_scores.items():
            if score is not None:
                desc = _describe_factor(dim, score)
                contributions.append(FactorContribution(
                    factor=dim,
                    score=round(score, 3),
                    description=desc,
                ))

        contributions.sort(key=lambda c: c.score, reverse=True)
        top_factors = contributions[:5]
        concerns = [c for c in contributions if c.score < 0.4][:3]

        # Tradeoffs
        tradeoffs = _generate_tradeoffs(sm, requirements)

        results.append(RecommendationResult(
            material_id=sm.material_id,
            material_name=sm.material_name,
            category=sm.category,
            score=round(sm.total_score, 3),
            confidence=sm.confidence,
            top_factors=top_factors,
            concerns=concerns,
            unmet_constraints=sm.hard_failures,
            tradeoffs=tradeoffs,
        ))

    return RecommendationResponse(
        recommendations=results,
        scoring_version=settings.SCORING_CONFIG_VERSION,
        total_materials_evaluated=len(materials),
        materials_filtered_out=filtered_count,
    )


# ─── Explanation Helpers ───────────────────────────────────────────

_FACTOR_LABELS = {
    "tensile_strength": "Tensile Strength",
    "elastic_modulus": "Elastic Modulus",
    "elongation": "Elongation at Break",
    "puncture_resistance": "Puncture Resistance",
    "wvtr": "Water Vapor Barrier (WVTR)",
    "otr": "Oxygen Barrier (OTR)",
    "biocompatibility": "Biocompatibility",
    "degradation": "Degradation Timeline",
    "hydrolytic_stability": "Hydrolytic Stability",
    "cost": "Cost",
    "availability": "Availability",
}


def _describe_factor(dim: str, score: float) -> str:
    label = _FACTOR_LABELS.get(dim, dim.replace("_", " ").title())
    if score >= 0.9:
        return f"{label}: Excellent match with target requirements"
    elif score >= 0.7:
        return f"{label}: Good match, within acceptable range"
    elif score >= 0.4:
        return f"{label}: Partial match, some deviation from target"
    else:
        return f"{label}: Poor match, significant gap from requirements"


def _generate_tradeoffs(sm: ScoredMaterial, req: RequirementInput) -> list[str]:
    tradeoffs = []
    scores = sm.dimension_scores

    # High mechanical but poor barrier
    mech_avg = _avg_non_none([scores.get("tensile_strength"), scores.get("elastic_modulus")])
    barrier_avg = _avg_non_none([scores.get("wvtr"), scores.get("otr")])
    if mech_avg and barrier_avg:
        if mech_avg > 0.7 and barrier_avg < 0.4:
            tradeoffs.append("Strong mechanical properties but weak barrier performance — consider blending or coating")
        elif barrier_avg > 0.7 and mech_avg < 0.4:
            tradeoffs.append("Good barrier properties but limited mechanical strength — consider reinforcement additives")

    # Good biocompatibility but limited processing
    bio = scores.get("biocompatibility")
    if bio and bio > 0.7:
        tradeoffs.append("Biocompatible material — verify specific regulatory pathway for your application")

    # Low evidence
    if sm.evidence_level == "low":
        tradeoffs.append("⚠ Evidence level is LOW — properties are based on limited or synthetic data")

    # Cost vs performance
    cost_score = scores.get("cost")
    if cost_score and cost_score < 0.5 and sm.total_score > 0.7:
        tradeoffs.append("High-performing material but cost may be prohibitive — evaluate cost-benefit")

    return tradeoffs


def _avg_non_none(values: list[float | None]) -> float | None:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None
