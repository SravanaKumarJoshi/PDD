"""
Safety & constraint enforcement layer.
Runs BEFORE any ML model — hard-rejects unsafe materials.
"""
import pandas as pd
from dataclasses import dataclass, field


@dataclass
class SafetyResult:
    approved: pd.DataFrame
    rejected: list[dict] = field(default_factory=list)
    warnings: dict[str, list[str]] = field(default_factory=dict)


def run_safety_gate(
    df: pd.DataFrame,
    requirements: dict,
) -> SafetyResult:
    """
    Pre-ML safety filter. Returns approved materials and rejection reasons.

    Hard reject rules:
      - toxicity_score < 3
      - biocompatibility < user minimum (default 5)
      - biodegradation outside 1-1000 days
      - required sterilization not supported
    """
    result = SafetyResult(approved=pd.DataFrame())
    approved_idx = []
    warnings = {}

    min_biocompat = requirements.get("min_biocompatibility", 5)
    req_gamma = requirements.get("sterilization_gamma", False)
    req_eto = requirements.get("sterilization_eto", False)
    req_steam = requirements.get("sterilization_steam", False)

    for idx, row in df.iterrows():
        polymer_name = row["polymer"]
        reasons = []

        # Hard reject: toxicity
        if row.get("toxicity_score", 10) < 3:
            reasons.append("Fails cytotoxicity safety threshold (toxicity_score < 3)")

        # Hard reject: biocompatibility
        if row.get("biocompatibility", 0) < min_biocompat:
            reasons.append(
                f"Insufficient biocompatibility ({row['biocompatibility']} < {min_biocompat})"
            )

        # Hard reject: degradation out of range
        bd = row.get("biodegradation_days", 0)
        if bd < 1 or bd > 1000:
            reasons.append(f"Non-compliant degradation ({bd} days, must be 1-1000)")

        # Hard reject: sterilization
        if req_gamma and row.get("sterilization_gamma", 0) != 1:
            reasons.append("Does not support gamma sterilization")
        if req_eto and row.get("sterilization_eto", 0) != 1:
            reasons.append("Does not support EtO sterilization")
        if req_steam and row.get("sterilization_steam", 0) != 1:
            reasons.append("Does not support steam sterilization")

        if reasons:
            result.rejected.append({
                "polymer": polymer_name,
                "reasons": reasons,
            })
            continue

        # Soft warnings (material proceeds but flagged)
        w = []
        if row.get("evidence_level", "low") == "low":
            w.append("Limited evidence — verify experimentally")
        if row.get("is_augmented", 0) == 1:
            w.append("Based on augmented data — lower confidence")
        if row.get("data_completeness", 1.0) < 0.7:
            w.append("Incomplete data — predictions less reliable")

        if w:
            warnings[polymer_name] = w

        approved_idx.append(idx)

    result.approved = df.loc[approved_idx].copy()
    result.warnings = warnings
    return result
