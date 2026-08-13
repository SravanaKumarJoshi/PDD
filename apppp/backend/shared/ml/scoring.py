"""Single authoritative multi-criteria weighted scoring engine."""

import os
import math
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from shared.ml.config import SCREENING_CONFIG

RULE_SCORE_WEIGHT = float(os.getenv("RULE_SCORE_WEIGHT", "0.7"))
ML_SCORE_WEIGHT = float(os.getenv("ML_SCORE_WEIGHT", "0.3"))


def _clean_val(v: Any) -> Any:
    """Return None if value is None, NaN, or pd.NA, else return python native type."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if pd.isna(v):
        return None
    return v


def calculate_material_score_details(
    material_row: pd.Series,
    requirements: Dict[str, Any],
    weights: Dict[str, float] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Calculate multi-criteria weighted match score (0.0 to 100.0) and full breakdown.

    Scores ONLY criteria explicitly requested by the user.
    """
    category_breakdown: Dict[str, Any] = {}
    active_weights_sum = 0.0
    weighted_scores_sum = 0.0

    # Mechanical
    mech_props = {}
    target_tensile = _clean_val(requirements.get("tensile_strength"))
    if target_tensile is not None and float(target_tensile) > 0:
        act_tensile = _clean_val(material_row.get("tensile_strength"))
        if act_tensile is not None and float(act_tensile) >= 0:
            target_val = float(target_tensile)
            act_val = float(act_tensile)
            if act_val < target_val:
                match_pct = max(0.0, 70.0 * (act_val / target_val))
            else:
                surplus = (act_val - target_val) / target_val
                match_pct = min(100.0, 80.0 + 20.0 * min(1.0, surplus))
            mech_props["tensile_strength"] = {
                "requested": f">= {target_tensile} MPa",
                "actual": float(act_tensile),
                "match_pct": round(match_pct, 1),
                "is_used": True,
                "is_missing": False,
                "penalty_applied": None if match_pct >= 80.0 else f"Below target ({round(match_pct, 1)}%)",
            }
        else:
            mech_props["tensile_strength"] = {
                "requested": f">= {target_tensile} MPa",
                "actual": None,
                "match_pct": 25.0,
                "is_used": False,
                "is_missing": True,
                "penalty_applied": "Missing property value in database (25% penalty)",
            }

    target_modulus = _clean_val(requirements.get("elastic_modulus"))
    if target_modulus is not None and float(target_modulus) > 0:
        act_modulus = _clean_val(material_row.get("elastic_modulus"))
        if act_modulus is not None and float(act_modulus) >= 0:
            target_val = float(target_modulus)
            act_val = float(act_modulus)
            diff = abs(act_val - target_val)
            if diff <= target_val * 0.1:
                match_pct = 100.0 - 15.0 * (diff / (target_val * 0.1))
            else:
                gap = diff - target_val * 0.1
                match_pct = max(0.0, 85.0 - 70.0 * (gap / target_val))
            mech_props["elastic_modulus"] = {
                "requested": f"~ {target_modulus} GPa",
                "actual": float(act_modulus),
                "match_pct": round(match_pct, 1),
                "is_used": True,
                "is_missing": False,
                "penalty_applied": None if match_pct >= 80.0 else f"Deviation from target ({round(match_pct, 1)}%)",
            }
        else:
            mech_props["elastic_modulus"] = {
                "requested": f"~ {target_modulus} GPa",
                "actual": None,
                "match_pct": 25.0,
                "is_used": False,
                "is_missing": True,
                "penalty_applied": "Missing property value in database (25% penalty)",
            }

    if mech_props:
        w = float((weights or {}).get("mechanical", requirements.get("weight_mechanical", 1.0)))
        matches = [p["match_pct"] for p in mech_props.values()]
        cat_score = sum(matches) / len(matches) if matches else 0.0
        category_breakdown["mechanical"] = {
            "weight": w,
            "score": round(cat_score, 1),
            "properties": mech_props,
        }
        weighted_scores_sum += cat_score * w
        active_weights_sum += w

    # Barrier (WVTR / Oxygen Permeability)
    barrier_props = {}
    target_wvtr = _clean_val(requirements.get("wvtr"))
    if target_wvtr is not None and float(target_wvtr) > 0:
        act_wvtr = _clean_val(material_row.get("wvtr"))
        if act_wvtr is not None and float(act_wvtr) >= 0:
            target_val = float(target_wvtr)
            act_val = float(act_wvtr)
            if act_val <= target_val:
                margin = (target_val - act_val) / target_val
                match_pct = min(100.0, 85.0 + 15.0 * margin)
                penalty = None
            else:
                ratio = target_val / act_val
                match_pct = max(0.0, 85.0 * ratio)
                penalty = f"Exceeds max WVTR limit ({act_val} > {target_val})"
            barrier_props["wvtr"] = {
                "requested": f"<= {target_wvtr} g/m2/day",
                "actual": float(act_wvtr),
                "match_pct": round(match_pct, 1),
                "is_used": True,
                "is_missing": False,
                "penalty_applied": penalty,
            }
        else:
            barrier_props["wvtr"] = {
                "requested": f"<= {target_wvtr} g/m2/day",
                "actual": None,
                "match_pct": 25.0,
                "is_used": False,
                "is_missing": True,
                "penalty_applied": "Missing property value in database (25% penalty)",
            }

    if barrier_props:
        w = float((weights or {}).get("barrier", requirements.get("weight_barrier", 1.0)))
        matches = [p["match_pct"] for p in barrier_props.values()]
        cat_score = sum(matches) / len(matches) if matches else 0.0
        category_breakdown["barrier"] = {
            "weight": w,
            "score": round(cat_score, 1),
            "properties": barrier_props,
        }
        weighted_scores_sum += cat_score * w
        active_weights_sum += w

    # Biological (Biocompatibility rating)
    bio_props = {}
    min_biocompat = _clean_val(requirements.get("min_biocompatibility"))
    if min_biocompat is not None:
        act_biocompat = _clean_val(material_row.get("biocompatibility"))
        if act_biocompat is not None:
            target_val = max(float(min_biocompat), 1.0)
            act_val = float(act_biocompat)
            if act_val >= target_val:
                match_pct = min(100.0, 80.0 + 20.0 * min(1.0, (act_val - target_val) / target_val))
            else:
                match_pct = max(0.0, 70.0 * (act_val / target_val))
            bio_props["biocompatibility"] = {
                "requested": f">= {min_biocompat} / 10",
                "actual": float(act_biocompat),
                "match_pct": round(match_pct, 1),
                "is_used": True,
                "is_missing": False,
                "penalty_applied": None if match_pct >= 80.0 else f"Below minimum biocompatibility ({act_biocompat} < {min_biocompat})",
            }
        else:
            bio_props["biocompatibility"] = {
                "requested": f">= {min_biocompat} / 10",
                "actual": None,
                "match_pct": 25.0,
                "is_used": False,
                "is_missing": True,
                "penalty_applied": "Missing property value in database (25% penalty)",
            }

    if bio_props:
        w = float((weights or {}).get("biological", requirements.get("weight_biological", 1.2)))
        matches = [p["match_pct"] for p in bio_props.values()]
        cat_score = sum(matches) / len(matches) if matches else 0.0
        category_breakdown["biological"] = {
            "weight": w,
            "score": round(cat_score, 1),
            "properties": bio_props,
        }
        weighted_scores_sum += cat_score * w
        active_weights_sum += w

    # Degradation
    deg_props = {}
    target_biodeg = _clean_val(requirements.get("target_biodegradation_days"))
    if target_biodeg is not None and float(target_biodeg) > 0:
        act_biodeg = _clean_val(material_row.get("biodegradation_days"))
        if act_biodeg is not None:
            target_val = float(target_biodeg)
            act_val = float(act_biodeg)
            diff = abs(act_val - target_val)
            if diff <= target_val * 0.15:
                match_pct = 100.0 - 15.0 * (diff / (target_val * 0.15))
            else:
                gap = diff - target_val * 0.15
                match_pct = max(0.0, 85.0 - 70.0 * (gap / target_val))
            deg_props["biodegradation_days"] = {
                "requested": f"~ {target_biodeg} days",
                "actual": float(act_biodeg),
                "match_pct": round(match_pct, 1),
                "is_used": True,
                "is_missing": False,
                "penalty_applied": None if match_pct >= 80.0 else f"Deviation from target ({act_biodeg} vs {target_biodeg} days)",
            }
        else:
            deg_props["biodegradation_days"] = {
                "requested": f"~ {target_biodeg} days",
                "actual": None,
                "match_pct": 25.0,
                "is_used": False,
                "is_missing": True,
                "penalty_applied": "Missing property value in database (25% penalty)",
            }

    if deg_props:
        w = float((weights or {}).get("degradation", requirements.get("weight_degradation", 1.0)))
        matches = [p["match_pct"] for p in deg_props.values()]
        cat_score = sum(matches) / len(matches) if matches else 0.0
        category_breakdown["degradation"] = {
            "weight": w,
            "score": round(cat_score, 1),
            "properties": deg_props,
        }
        weighted_scores_sum += cat_score * w
        active_weights_sum += w

    final_rule_score = (weighted_scores_sum / active_weights_sum) if active_weights_sum > 0 else 0.0
    return round(float(np.clip(final_rule_score, 0.0, 100.0)), 2), category_breakdown


def calculate_material_score(
    material_row: pd.Series,
    requirements: Dict[str, Any],
    weights: Dict[str, float] = None,
) -> float:
    """Calculate multi-criteria weighted match score (0.0 to 1.0)."""
    rule_score_100, _ = calculate_material_score_details(material_row, requirements, weights)
    return round(rule_score_100 / 100.0, 4)


def rank_candidates(
    candidates_df: pd.DataFrame,
    ml_probabilities: np.ndarray,
    requirements: Dict[str, Any],
    alpha: float = 1.0,
) -> pd.DataFrame:
    """Rank candidate materials using multi-criteria rule matching and ML model probabilities."""
    results_df = candidates_df.copy()

    if hasattr(ml_probabilities, "ndim") and ml_probabilities.ndim == 2 and ml_probabilities.shape[1] > 1:
        ml_probs_1d = ml_probabilities[:, 1]
    else:
        ml_probs_1d = np.asarray(ml_probabilities).ravel()

    rule_scores = []
    score_breakdowns = []

    for idx, row in results_df.iterrows():
        rule_score, breakdown = calculate_material_score_details(row, requirements)
        rule_scores.append(rule_score)
        score_breakdowns.append(breakdown)

    results_df["ml_probability"] = np.round(np.clip(ml_probs_1d, 0.0, 1.0), 4)
    results_df["ml_score"] = np.round(results_df["ml_probability"] * 100.0, 2)
    results_df["rule_score"] = rule_scores
    results_df["multi_criteria_score"] = results_df["rule_score"]
    results_df["score_breakdown"] = score_breakdowns

    # Compute blended final score
    raw_final = (results_df["rule_score"] * RULE_SCORE_WEIGHT) + (results_df["ml_score"] * ML_SCORE_WEIGHT)
    results_df["final_score"] = np.round(np.clip(raw_final, 0.0, 100.0), 2)

    # Sort deterministically
    results_df = results_df.sort_values(
        by=["final_score", "rule_score", "ml_probability"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    # Assign rank
    results_df["rank"] = results_df.index + 1
    return results_df
