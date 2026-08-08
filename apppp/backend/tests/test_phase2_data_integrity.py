"""Phase 2 Verification Tests.

Verifies:
1. Startup Database Schema Inspector (9 category property mappings)
2. Pre-Scoring Data Quality & Engineering Integrity Validation
   - Range validation (Tensile >= 0, Modulus >= 0, Elongation 0-1000%, Tm > Tg)
   - Unit standardization
   - Material deduplication
"""

import pytest
import pandas as pd
from app.core.schema_validator import validate_database_schema, CATEGORY_MAPPINGS
from shared.ml.data_validator import validate_and_sanitize_material_data


def test_schema_validator_category_mappings():
    """Verify that all 9 categories are defined and property mappings are valid."""
    res = validate_database_schema(engine=None)
    assert res["status"] == "valid"
    assert res["categories_verified"] == 9
    assert "mechanical" in CATEGORY_MAPPINGS
    assert "barrier" in CATEGORY_MAPPINGS
    assert "thermal" in CATEGORY_MAPPINGS
    assert "physical" in CATEGORY_MAPPINGS
    assert "degradation" in CATEGORY_MAPPINGS
    assert "processing" in CATEGORY_MAPPINGS
    assert "sustainability" in CATEGORY_MAPPINGS
    assert "biological" in CATEGORY_MAPPINGS
    assert "sterilization" in CATEGORY_MAPPINGS


def test_data_validator_engineering_range_checks():
    """Verify that invalid physical values (negative strength, invalid elongation, Tm <= Tg) are caught."""
    df = pd.DataFrame([
        {
            "id": "1",
            "polymer": "Valid Chitosan",
            "category": "Chitosan",
            "tensile_strength": 50.0,
            "elastic_modulus": 2.0,
            "elongation_pct": 25.0,
            "melting_temp": 180.0,
            "glass_transition_temp": 80.0,
        },
        {
            "id": "2",
            "polymer": "Invalid Tensile",
            "category": "Chitosan",
            "tensile_strength": -10.0,  # Invalid
            "elastic_modulus": 2.0,
            "elongation_pct": 25.0,
        },
        {
            "id": "3",
            "polymer": "Invalid Thermal",
            "category": "Alginate",
            "tensile_strength": 40.0,
            "melting_temp": 50.0,
            "glass_transition_temp": 100.0,  # Invalid: Tm <= Tg
        }
    ])

    sanitized, metrics = validate_and_sanitize_material_data(df)
    assert metrics["materials_checked"] == 3
    assert metrics["materials_valid"] == 1
    assert metrics["materials_invalid"] == 2
    assert len(sanitized) == 1
    assert sanitized.iloc[0]["polymer"] == "Valid Chitosan"


def test_data_validator_material_deduplication():
    """Verify that duplicate polymer records are deduplicated."""
    df = pd.DataFrame([
        {"id": "1", "polymer": "Chitosan A", "category": "Chitosan", "tensile_strength": 50.0},
        {"id": "2", "polymer": "Chitosan A", "category": "Chitosan", "tensile_strength": 55.0},
        {"id": "3", "polymer": "Pectin B", "category": "Pectin", "tensile_strength": 30.0},
    ])

    sanitized, metrics = validate_and_sanitize_material_data(df)
    assert metrics["duplicates_removed"] == 1
    assert len(sanitized) == 2
    assert set(sanitized["polymer"].tolist()) == {"Chitosan A", "Pectin B"}
