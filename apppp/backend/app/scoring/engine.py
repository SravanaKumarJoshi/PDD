"""Transparent weighted scoring engine for biopolymer recommendations.

Implements a 6-phase pipeline:
1. Active requirement detection & Hard constraint filtering
2. Numeric range & distance scoring
3. Boolean/categorical scoring
4. Weighted aggregation (0.0 to 100.0% scale)
5. Confidence computation
6. Explanation generation & Ranking
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from app.schemas.recommendation import (
    RequirementInput,
    RecommendationResult,
    RecommendationResponse,
    FactorContribution,
)
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScoredMaterial:
    material_id: str
    material_name: str
    category: str
    evidence_level: str
    data_completeness: float
    dimension_scores: dict[str, float | None] = field(default_factory=dict)
    missing_dimensions: list[str] = field(default_factory=list)
    hard_failures: list[str] = field(default_factory=list)
    total_score: float = 0.0
    confidence: float = 0.0


MISSING_DATA_SCORE_PENALTY = 25.0  # 25% penalty score for missing properties on requested criteria


# ─── Scoring Helpers ──────────────────────────────────────────────

def score_min_requirement(actual_val: float | None, target_min: float | None) -> float:
    """Continuous distance score for minimum requirement (e.g. Tensile Strength >= X)."""
    if target_min is None:
        return 100.0
    if actual_val is None:
        return MISSING_DATA_SCORE_PENALTY
    if target_min <= 0:
        return 100.0

    if actual_val < target_min:
        # Below minimum: continuous decay based on ratio
        ratio = max(0.0, actual_val / target_min)
        return max(0.0, round(70.0 * ratio, 2))
    else:
        # Meets minimum: scales from 80% (at min) up to 100% (at 2.0x min surplus)
        surplus_ratio = (actual_val - target_min) / target_min
        return min(100.0, round(80.0 + 20.0 * min(1.0, surplus_ratio), 2))


def score_max_requirement(actual_val: float | None, target_max: float | None) -> float:
    """Continuous distance score for maximum requirement."""
    if target_max is None:
        return 100.0
    if actual_val is None:
        return MISSING_DATA_SCORE_PENALTY
    if target_max <= 0:
        return 100.0

    if actual_val <= target_max:
        # Under max: scales from 85% at max bound up to 100% at lower values
        margin_ratio = (target_max - actual_val) / target_max
        return min(100.0, round(85.0 + 15.0 * min(1.0, margin_ratio), 2))
    else:
        # Exceeds max: continuous inverse ratio decay
        ratio = target_max / actual_val
        return max(0.0, round(85.0 * ratio, 2))


def score_range_requirement(
    actual_min: float | None, actual_max: float | None,
    target_min: float | None, target_max: float | None
) -> float:
    """Continuous distance score for range requirement (e.g. Elastic Modulus, Degradation days)."""
    if target_min is None and target_max is None:
        return 100.0

    # Fallback to single bounds if only one target bound specified
    if target_min is not None and target_max is None:
        act_val = actual_max if actual_max is not None else actual_min
        return score_min_requirement(act_val, target_min)
    if target_max is not None and target_min is None:
        act_val = actual_min if actual_min is not None else actual_max
        return score_max_requirement(act_val, target_max)

    if actual_min is None and actual_max is None:
        return MISSING_DATA_SCORE_PENALTY

    if target_max <= target_min:
        return 100.0

    act_min = actual_min if actual_min is not None else actual_max
    act_max = actual_max if actual_max is not None else actual_min
    if act_min is None or act_max is None:
        return MISSING_DATA_SCORE_PENALTY

    target_mid = (target_min + target_max) / 2.0
    target_half = (target_max - target_min) / 2.0
    act_mid = (act_min + act_max) / 2.0

    diff = abs(act_mid - target_mid)
    if diff <= target_half:
        # Inside target range: 100% at center, 85% at range edges
        ratio = diff / target_half if target_half > 0 else 0.0
        return round(100.0 - 15.0 * ratio, 2)
    else:
        # Outside target range: continuous distance penalty decay
        gap = diff - target_half
        span = target_half if target_half > 0 else (target_mid if target_mid > 0 else 1.0)
        return max(0.0, round(85.0 - 70.0 * (gap / span), 2))


def score_inverse_point(actual_val: float | None, target_max: float | None) -> float:
    """For properties where lower is better (WVTR, OTR)."""
    return score_max_requirement(actual_val, target_max)


def score_ordinal_band(
    actual_band: str | None,
    target_band: str | None,
    higher_is_better: bool = False
) -> float:
    """Score cost/availability bands ("low", "med", "high")."""
    if target_band is None:
        return 100.0
    if actual_band is None:
        return MISSING_DATA_SCORE_PENALTY

    band_order = {"low": 1, "med": 2, "high": 3}
    actual_val = band_order.get(str(actual_band).lower(), 2)
    target_val = band_order.get(str(target_band).lower(), 3)

    if higher_is_better:
        if actual_val > target_val:
            return 100.0
        elif actual_val == target_val:
            return 85.0
        else:
            diff = target_val - actual_val
            return 45.0 if diff == 1 else 15.0
    else:
        if actual_val < target_val:
            return 100.0
        elif actual_val == target_val:
            return 85.0
        else:
            diff = actual_val - target_val
            return 45.0 if diff == 1 else 15.0


def has_any_requirement(req: RequirementInput) -> bool:
    m = req.mechanical
    b = req.barrier
    bio = req.biological
    d = req.degradation
    p = req.processing
    s = req.sterilization
    cost = req.cost
    
    num_fields = [
        m.tensile_strength_min, m.tensile_strength_max, m.elastic_modulus_min, m.elastic_modulus_max,
        m.elongation_min, m.elongation_max, m.puncture_resistance_min, b.wvtr_max, b.otr_max,
        d.degradation_days_min, d.degradation_days_max, d.hydrolytic_stability_min,
        cost.max_cost_band, cost.min_availability_band
    ]
    bool_fields = [
        bio.cytotoxicity_safe_required, bio.hemocompatible_required, bio.antimicrobial_required, bio.low_endotoxin_required,
        d.enzymatic_required, p.film_required, p.casting_required, p.extrusion_required, p.coating_required, p.melt_required,
        s.gamma_required, s.eto_required, s.steam_required, s.uv_required, s.autoclave_required
    ]
    return any(f is not None for f in num_fields) or any(bool_fields)


# ─── Main Scoring Function ────────────────────────────────────────

def score_and_rank(
    requirements: RequirementInput,
    materials: list[dict],
) -> RecommendationResponse:
    """Run full scoring pipeline on materials with 0.0 to 100.0% output score scale."""
    if not has_any_requirement(requirements):
        return RecommendationResponse(
            recommendations=[],
            scoring_version=settings.SCORING_CONFIG_VERSION,
            total_materials_evaluated=len(materials),
            materials_filtered_out=0,
        )

    # Determine active requirements and weights
    req_m = requirements.mechanical
    req_bar = requirements.barrier
    req_b = requirements.biological
    req_d = requirements.degradation
    req_p = requirements.processing
    req_s = requirements.sterilization
    req_c = requirements.cost

    active_weights: dict[str, float] = {}

    if req_m.tensile_strength_min is not None or req_m.tensile_strength_max is not None:
        active_weights["tensile_strength"] = req_m.weight
    if req_m.elastic_modulus_min is not None or req_m.elastic_modulus_max is not None:
        active_weights["elastic_modulus"] = req_m.weight
    if req_m.elongation_min is not None or req_m.elongation_max is not None:
        active_weights["elongation"] = req_m.weight
    if req_m.puncture_resistance_min is not None:
        active_weights["puncture_resistance"] = req_m.weight

    if req_bar.wvtr_max is not None:
        active_weights["wvtr"] = req_bar.weight
    if req_bar.otr_max is not None:
        active_weights["otr"] = req_bar.weight

    if req_d.degradation_days_min is not None or req_d.degradation_days_max is not None:
        active_weights["degradation"] = req_d.weight
    if req_d.hydrolytic_stability_min is not None:
        active_weights["hydrolytic_stability"] = req_d.weight

    if (req_b.cytotoxicity_safe_required or req_b.hemocompatible_required or 
            req_b.antimicrobial_required or req_b.low_endotoxin_required):
        active_weights["biocompatibility"] = req_b.weight

    if req_c.max_cost_band is not None:
        active_weights["cost"] = req_c.weight
    if req_c.min_availability_band is not None:
        active_weights["availability"] = req_c.weight

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

        if req_b.cytotoxicity_safe_required and not props.get("cytotoxicity_safe"):
            sm.hard_failures.append("Does not meet cytotoxicity safety requirement")
        if req_b.hemocompatible_required and not props.get("hemocompatible"):
            sm.hard_failures.append("Does not meet hemocompatibility requirement")

        if sm.hard_failures:
            filtered_count += 1
            continue

        # ── PHASE 2: Continuous Criterion Scoring ────────────
        if "tensile_strength" in active_weights:
            sm.dimension_scores["tensile_strength"] = score_range_requirement(
                props.get("tensile_strength_mpa_min"), props.get("tensile_strength_mpa_max"),
                req_m.tensile_strength_min, req_m.tensile_strength_max,
            )
        if "elastic_modulus" in active_weights:
            sm.dimension_scores["elastic_modulus"] = score_range_requirement(
                props.get("elastic_modulus_gpa_min"), props.get("elastic_modulus_gpa_max"),
                req_m.elastic_modulus_min, req_m.elastic_modulus_max,
            )
        if "elongation" in active_weights:
            sm.dimension_scores["elongation"] = score_range_requirement(
                props.get("elongation_pct_min"), props.get("elongation_pct_max"),
                req_m.elongation_min, req_m.elongation_max,
            )
        if "puncture_resistance" in active_weights:
            sm.dimension_scores["puncture_resistance"] = score_min_requirement(
                props.get("puncture_resistance_n"), req_m.puncture_resistance_min
            )

        if "wvtr" in active_weights:
            sm.dimension_scores["wvtr"] = score_inverse_point(
                props.get("wvtr"), req_bar.wvtr_max
            )
        if "otr" in active_weights:
            sm.dimension_scores["otr"] = score_inverse_point(
                props.get("otr"), req_bar.otr_max
            )

        if "degradation" in active_weights:
            sm.dimension_scores["degradation"] = score_range_requirement(
                props.get("degradation_days_min"), props.get("degradation_days_max"),
                req_d.degradation_days_min, req_d.degradation_days_max,
            )
        if "hydrolytic_stability" in active_weights:
            sm.dimension_scores["hydrolytic_stability"] = score_ordinal_band(
                props.get("hydrolytic_stability"), req_d.hydrolytic_stability_min, higher_is_better=True
            )

        if "biocompatibility" in active_weights:
            bio_scores = []
            if req_b.cytotoxicity_safe_required:
                bio_scores.append(100.0 if props.get("cytotoxicity_safe") is True else (20.0 if props.get("cytotoxicity_safe") is False else MISSING_DATA_SCORE_PENALTY))
            if req_b.hemocompatible_required:
                bio_scores.append(100.0 if props.get("hemocompatible") is True else (20.0 if props.get("hemocompatible") is False else MISSING_DATA_SCORE_PENALTY))
            if req_b.antimicrobial_required:
                bio_scores.append(100.0 if props.get("antimicrobial") is True else (20.0 if props.get("antimicrobial") is False else MISSING_DATA_SCORE_PENALTY))
            if req_b.low_endotoxin_required:
                bio_scores.append(100.0 if props.get("low_endotoxin") is True else (20.0 if props.get("low_endotoxin") is False else MISSING_DATA_SCORE_PENALTY))
            
            sm.dimension_scores["biocompatibility"] = (
                sum(bio_scores) / len(bio_scores) if bio_scores else MISSING_DATA_SCORE_PENALTY
            )

        if "cost" in active_weights:
            sm.dimension_scores["cost"] = score_ordinal_band(
                props.get("cost_band"), req_c.max_cost_band, higher_is_better=False
            )
        if "availability" in active_weights:
            sm.dimension_scores["availability"] = score_ordinal_band(
                props.get("availability_band"), req_c.min_availability_band, higher_is_better=True
            )

        # ── PHASE 3: Weighted Aggregation ─────────────────────
        total_weighted = 0.0
        total_weight = 0.0

        for dim, weight in active_weights.items():
            score = sm.dimension_scores.get(dim)
            if score is not None:
                total_weighted += weight * score
                total_weight += weight
                if score == MISSING_DATA_SCORE_PENALTY:
                    sm.missing_dimensions.append(dim)
                
                logger.debug(
                    f"Scoring [{sm.material_name}]: factor={dim}, score={score:.1f}%, weight={weight:.2f}"
                )

        raw_score = (total_weighted / total_weight) if total_weight > 0 else 0.0
        sm.total_score = round(max(0.0, min(100.0, raw_score)), 1)
        assert 0.0 <= sm.total_score <= 100.0, f"Final score out of bounds: {sm.total_score}"

        # ── PHASE 4: Confidence ───────────────────────────────
        evidence_map = {"low": 0.4, "med": 0.7, "high": 1.0}
        ev_score = evidence_map.get(sm.evidence_level, 0.4)
        sm.confidence = round(
            0.6 * sm.data_completeness + 0.4 * ev_score, 3
        )

        scored.append(sm)

    # ── PHASE 5: Explanation Generation & Rank ────────────────
    results: list[RecommendationResult] = []
    scored.sort(key=lambda x: x.total_score, reverse=True)

    for sm in scored:
        contributions = []
        for dim, score in sm.dimension_scores.items():
            if score is not None:
                is_missing = dim in sm.missing_dimensions
                desc = _describe_factor(dim, score, is_missing=is_missing)
                contributions.append(FactorContribution(
                    factor=dim,
                    score=round(score, 1),
                    description=desc,
                ))

        contributions.sort(key=lambda c: c.score, reverse=True)
        top_factors = [c for c in contributions if c.score >= 70.0][:5]
        concerns = [c for c in contributions if c.score < 50.0][:3]

        tradeoffs = _generate_tradeoffs(sm, requirements)

        results.append(RecommendationResult(
            material_id=sm.material_id,
            material_name=sm.material_name,
            category=sm.category,
            score=sm.total_score,
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


def _describe_factor(dim: str, score: float, is_missing: bool = False) -> str:
    label = _FACTOR_LABELS.get(dim, dim.replace("_", " ").title())
    if is_missing:
        return f"{label}: Data missing for requested requirement (25% penalty)"
    if score >= 90.0:
        return f"{label}: Excellent match with target requirements ({score:.1f}%)"
    elif score >= 80.0:
        return f"{label}: Very good match, meets requirements comfortably ({score:.1f}%)"
    elif score >= 70.0:
        return f"{label}: Good match, within acceptable range ({score:.1f}%)"
    elif score >= 50.0:
        return f"{label}: Moderate match, minor deviation from target ({score:.1f}%)"
    elif score >= 30.0:
        return f"{label}: Weak match, noticeable gap from requirements ({score:.1f}%)"
    else:
        return f"{label}: Poor match, significant gap from requirements ({score:.1f}%)"


def _generate_tradeoffs(sm: ScoredMaterial, req: RequirementInput) -> list[str]:
    tradeoffs = []
    scores = sm.dimension_scores

    if sm.missing_dimensions:
        missing_names = [_FACTOR_LABELS.get(d, d) for d in sm.missing_dimensions]
        tradeoffs.append(f"⚠ Missing data for requested properties: {', '.join(missing_names)} (25% penalty applied)")

    mech_avg = _avg_non_none([scores.get("tensile_strength"), scores.get("elastic_modulus")])
    barrier_avg = _avg_non_none([scores.get("wvtr"), scores.get("otr")])
    if mech_avg and barrier_avg:
        if mech_avg > 70.0 and barrier_avg < 50.0:
            tradeoffs.append("Strong mechanical properties but weak barrier performance — consider blending or coating")
        elif barrier_avg > 70.0 and mech_avg < 50.0:
            tradeoffs.append("Good barrier properties but limited mechanical strength — consider reinforcement additives")

    bio = scores.get("biocompatibility")
    if bio and bio > 70.0:
        tradeoffs.append("Biocompatible material — verify specific regulatory pathway for your application")

    if sm.evidence_level == "low":
        tradeoffs.append("⚠ Evidence level is LOW — properties are based on limited or synthetic data")

    cost_score = scores.get("cost")
    if cost_score and cost_score < 50.0 and sm.total_score > 70.0:
        tradeoffs.append("High-performing material but cost may be prohibitive — evaluate cost-benefit")

    return tradeoffs


def _avg_non_none(values: list[float | None]) -> float | None:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None
