"""Input validation module."""

from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_input: Dict[str, Any] = field(default_factory=dict)

def validate_user_input(input_dict: Dict[str, Any]) -> ValidationResult:
    """Validate user screening requirements."""
    result = ValidationResult(sanitized_input=input_dict.copy())
    errors = result.errors
    warnings = result.warnings

    # Biocompatibility range check
    biocompat = input_dict.get("min_biocompatibility")
    if biocompat is not None and not (0 <= biocompat <= 10):
        errors.append(f"min_biocompatibility must be between 0 and 10 (got {biocompat})")

    # Positive value checks
    positive_fields = ["tensile_strength", "elastic_modulus", "wvtr", "oxygen_permeability"]
    for field in positive_fields:
        val = input_dict.get(field)
        if val is not None and val < 0:
            errors.append(f"{field} cannot be negative (got {val})")

    result.is_valid = len(errors) == 0
    return result
