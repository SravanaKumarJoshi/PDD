"""Pre-ML Safety Gate constraint enforcement layer."""

import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class SafetyResult:
    approved: pd.DataFrame
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    warnings: Dict[str, List[str]] = field(default_factory=dict)

def run_safety_gate(df: pd.DataFrame, requirements: Dict[str, Any]) -> SafetyResult:
    """Pre-ML safety filter. Returns approved materials and rejection reasons."""
    result = SafetyResult(approved=pd.DataFrame())
    approved_idx = []
    rejected = []
    warnings = {}

    min_biocompat = requirements.get("min_biocompatibility", 5.0)
    req_gamma = requirements.get("sterilization_gamma", False)
    req_eto = requirements.get("sterilization_eto", False)
    req_steam = requirements.get("sterilization_steam", False)

    for idx, row in df.iterrows():
        r = row.to_dict()
        polymer_name = str(r.get("polymer") or r.get("name") or f"material_{idx}")
        reasons = []

        # Hard reject: toxicity score < 3
        tox = float(r.get("toxicity_score", 10.0) if pd.notna(r.get("toxicity_score")) else 10.0)
        if tox < 3.0:
            reasons.append("Fails cytotoxicity threshold (toxicity_score < 3)")

        # Hard reject: biocompatibility < minimum
        bio = float(r.get("biocompatibility", 0.0) if pd.notna(r.get("biocompatibility")) else 0.0)
        if bio < min_biocompat:
            reasons.append(f"Insufficient biocompatibility ({bio} < {min_biocompat})")

        # Hard reject: degradation range
        bd = float(r.get("biodegradation_days", 0.0) if pd.notna(r.get("biodegradation_days")) else 0.0)
        if bd < 1.0 or bd > 1000.0:
            reasons.append(f"Non-compliant degradation ({bd} days, must be 1-1000)")

        # Hard reject: sterilization
        if req_gamma and float(r.get("sterilization_gamma", 0) if pd.notna(r.get("sterilization_gamma")) else 0) != 1:
            reasons.append("Does not support gamma sterilization")
        if req_eto and float(r.get("sterilization_eto", 0) if pd.notna(r.get("sterilization_eto")) else 0) != 1:
            reasons.append("Does not support EtO sterilization")
        if req_steam and float(r.get("sterilization_steam", 0) if pd.notna(r.get("sterilization_steam")) else 0) != 1:
            reasons.append("Does not support steam sterilization")

        if reasons:
            rejected.append({"polymer": polymer_name, "reasons": reasons})
            continue

        approved_idx.append(idx)

    result.approved = df.loc[approved_idx].copy() if approved_idx else pd.DataFrame()
    result.rejected = rejected
    result.warnings = warnings
    return result
