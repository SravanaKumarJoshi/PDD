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
    from src.data import standardize_material_dataframe
    df = standardize_material_dataframe(df)

    result = SafetyResult(approved=pd.DataFrame())
    approved_idx = []
    warnings = {}

    min_biocompat = float(requirements.get("min_biocompatibility", 5))
    req_gamma = bool(requirements.get("sterilization_gamma", False))
    req_eto = bool(requirements.get("sterilization_eto", False))
    req_steam = bool(requirements.get("sterilization_steam", False))

    for idx, row in df.iterrows():
        r = row.to_dict()
        polymer_name = str(r.get("polymer") or r.get("name") or f"Material #{idx}")
        reasons = []

        # Hard reject: toxicity
        tox_val = float(r.get("toxicity_score", 10) if pd.notna(r.get("toxicity_score")) else 10)
        if tox_val < 3:
            reasons.append("Fails cytotoxicity safety threshold (toxicity_score < 3)")

        # Hard reject: biocompatibility
        bio_val = float(r.get("biocompatibility", 0) if pd.notna(r.get("biocompatibility")) else 0)
        if bio_val < min_biocompat:
            reasons.append(
                f"Insufficient biocompatibility ({bio_val} < {min_biocompat})"
            )

        # Hard reject: degradation out of range
        bd = float(r.get("biodegradation_days", 0) if pd.notna(r.get("biodegradation_days")) else 0)
        if bd < 1 or bd > 1000:
            reasons.append(f"Non-compliant degradation ({bd} days, must be 1-1000)")

        # Hard reject: sterilization
        if req_gamma and float(r.get("sterilization_gamma", 0) if pd.notna(r.get("sterilization_gamma")) else 0) != 1:
            reasons.append("Does not support gamma sterilization")
        if req_eto and float(r.get("sterilization_eto", 0) if pd.notna(r.get("sterilization_eto")) else 0) != 1:
            reasons.append("Does not support EtO sterilization")
        if req_steam and float(r.get("sterilization_steam", 0) if pd.notna(r.get("sterilization_steam")) else 0) != 1:
            reasons.append("Does not support steam sterilization")

        if reasons:
            result.rejected.append({
                "polymer": polymer_name,
                "reasons": reasons,
            })
            continue

        # Soft warnings (material proceeds but flagged)
        w = []
        if str(r.get("evidence_level", "low")) == "low":
            w.append("Limited evidence — verify experimentally")
        if float(r.get("is_augmented", 0) if pd.notna(r.get("is_augmented")) else 0) == 1:
            w.append("Based on augmented data — lower confidence")
        if float(r.get("data_completeness", 1.0) if pd.notna(r.get("data_completeness")) else 1.0) < 0.7:
            w.append("Incomplete data — predictions less reliable")

        if w:
            warnings[polymer_name] = w

        approved_idx.append(idx)

    result.approved = df.loc[approved_idx].copy() if approved_idx else pd.DataFrame()
    result.warnings = warnings
    return result
