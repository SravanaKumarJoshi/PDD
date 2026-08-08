"""
Input validation layer — runs BEFORE pipeline.
Rejects invalid or dangerous user inputs with structured errors.
"""
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_input: dict = field(default_factory=dict)


def validate_user_input(input_dict: dict) -> ValidationResult:
    """
    Validate user requirements before pipeline processing.

    Checks:
    - No negative/zero physical values
    - Valid degradation ranges
    - Required fields present
    - Values within physically plausible bounds
    """
    result = ValidationResult(sanitized_input=input_dict.copy())
    errors = result.errors
    warnings = result.warnings

    # Required fields
    required = ["min_biocompatibility"]
    for field_name in required:
        if field_name not in input_dict:
            errors.append(f"Missing required field: {field_name}")

    # Physical value checks (must be positive)
    positive_fields = {
        "target_tensile_strength": (0, 500, "MPa"),
        "target_elastic_modulus": (0, 50, "GPa"),
        "target_wvtr": (0, 15000, "g/m²/day"),
        "target_oxygen_permeability": (0, 15000, "cc/m²/day"),
    }

    for field_name, (lo, hi, unit) in positive_fields.items():
        val = input_dict.get(field_name)
        if val is not None:
            if val <= 0:
                errors.append(
                    f"{field_name} must be positive (got {val} {unit})"
                )
            elif val > hi:
                warnings.append(
                    f"{field_name} = {val} {unit} is unusually high "
                    f"(typical range: {lo}-{hi})"
                )

    # Flexibility (1-10 scale)
    flex = input_dict.get("target_flexibility")
    if flex is not None and not (1 <= flex <= 10):
        errors.append(f"Flexibility must be 1-10 (got {flex})")

    # Biocompatibility (1-10)
    biocompat = input_dict.get("min_biocompatibility")
    if biocompat is not None and not (1 <= biocompat <= 10):
        errors.append(f"Biocompatibility must be 1-10 (got {biocompat})")

    # Degradation range
    biodeg_min = input_dict.get("biodeg_min", 0)
    biodeg_max = input_dict.get("biodeg_max", 0)
    if biodeg_min is not None and biodeg_max is not None:
        if biodeg_min < 0:
            errors.append(f"Biodegradation min cannot be negative ({biodeg_min})")
        if biodeg_max < biodeg_min:
            errors.append(
                f"Biodegradation max ({biodeg_max}) must be >= min ({biodeg_min})"
            )
        if biodeg_max > 1000:
            warnings.append(
                f"Biodegradation max = {biodeg_max} days is very high"
            )

    # Elongation
    elong = input_dict.get("target_elongation")
    if elong is not None and elong < 0:
        errors.append(f"Elongation cannot be negative ({elong}%)")

    result.is_valid = len(errors) == 0
    return result


def format_validation_errors(result: ValidationResult) -> str:
    """Format validation result as human-readable text."""
    lines = []
    if result.errors:
        lines.append("❌ **Validation Errors:**")
        for e in result.errors:
            lines.append(f"  - {e}")
    if result.warnings:
        lines.append("⚠️ **Warnings:**")
        for w in result.warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)
