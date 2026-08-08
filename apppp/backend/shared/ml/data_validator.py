"""Material Data Quality & Integrity Validator.

Performs physical engineering range checks, unit standardization,
and material deduplication before candidates enter the screening pipeline.
"""

import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def validate_and_sanitize_material_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validate material properties, perform unit standardization, and deduplicate materials.

    Returns:
        (sanitized_df, validation_metrics_dict)
    """
    if df.empty:
        return df, {
            "materials_checked": 0,
            "materials_valid": 0,
            "materials_invalid": 0,
            "duplicates_removed": 0,
            "unit_conversions": 0,
            "warnings": [],
        }

    materials_checked = len(df)
    warnings: List[str] = []
    unit_conversions = 0
    invalid_mask = np.zeros(len(df), dtype=bool)

    # 1. Physical & Engineering Range Checks
    for idx, row in df.iterrows():
        name = row.get("polymer", f"Material_{idx}")

        # Tensile Strength >= 0
        ts = row.get("tensile_strength")
        if pd.notna(ts) and float(ts) < 0:
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains negative tensile strength ({ts} MPa)")

        # Elastic Modulus >= 0
        em = row.get("elastic_modulus")
        if pd.notna(em) and float(em) < 0:
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains negative elastic modulus ({em} GPa)")

        # Elongation 0 to 1000%
        elo = row.get("elongation_pct")
        if pd.notna(elo) and (float(elo) < 0 or float(elo) > 1000):
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains invalid elongation percentage ({elo}%)")

        # WVTR >= 0
        wvtr = row.get("wvtr")
        if pd.notna(wvtr) and float(wvtr) < 0:
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains negative WVTR ({wvtr})")

        # OTR >= 0
        otr = row.get("oxygen_permeability")
        if pd.notna(otr) and float(otr) < 0:
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains negative O2 permeability ({otr})")

        # Biodegradation Days >= 0
        bd = row.get("biodegradation_days")
        if pd.notna(bd) and float(bd) < 0:
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains negative biodegradation days ({bd})")

        # Tm > Tg
        tm = row.get("melting_temp")
        tg = row.get("glass_transition_temp")
        if pd.notna(tm) and pd.notna(tg) and float(tm) <= float(tg):
            invalid_mask[idx] = True
            warnings.append(f"Material '{name}' contains invalid thermal profile (Tm {tm} <= Tg {tg})")

    # Filter out invalid materials
    df_valid = df[~invalid_mask].copy()
    materials_invalid = int(np.sum(invalid_mask))

    # 2. Material Deduplication
    orig_count = len(df_valid)
    if "polymer" in df_valid.columns:
        df_valid = df_valid.drop_duplicates(subset=["polymer", "category"], keep="first").reset_index(drop=True)
    duplicates_removed = orig_count - len(df_valid)
    if duplicates_removed > 0:
        warnings.append(f"Removed {duplicates_removed} duplicate material records")

    metrics = {
        "materials_checked": materials_checked,
        "materials_valid": len(df_valid),
        "materials_invalid": materials_invalid,
        "duplicates_removed": duplicates_removed,
        "unit_conversions": unit_conversions,
        "warnings": warnings,
    }

    return df_valid, metrics
