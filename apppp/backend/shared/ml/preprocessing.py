"""Input preprocessing and unit conversion helpers."""

from typing import Dict, Any

def normalize_input_requirements(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize input requirement fields and fill missing defaults."""
    normalized = input_dict.copy()

    # Map aliases
    if "target_tensile_strength" in normalized and "tensile_strength" not in normalized:
        normalized["tensile_strength"] = normalized["target_tensile_strength"]
    if "target_elastic_modulus" in normalized and "elastic_modulus" not in normalized:
        normalized["elastic_modulus"] = normalized["target_elastic_modulus"]
    if "target_wvtr" in normalized and "wvtr" not in normalized:
        normalized["wvtr"] = normalized["target_wvtr"]

    # Ensure min biocompatibility default
    if "min_biocompatibility" not in normalized:
        normalized["min_biocompatibility"] = 5.0

    return normalized
