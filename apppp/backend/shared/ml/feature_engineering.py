"""Feature engineering: extraction, transformation, and encoding."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from shared.ml.config import FEATURE_COLUMNS

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract and ensure all required feature columns exist in order."""
    X = pd.DataFrame(index=df.index)
    for col in FEATURE_COLUMNS:
        if col in df.columns:
            X[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            X[col] = 0.0
    return X[FEATURE_COLUMNS]

def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive non-linear features (e.g. ratio of tensile strength to elastic modulus)."""
    df_derived = df.copy()

    tensile = df_derived.get("tensile_strength", 0.0)
    elastic = df_derived.get("elastic_modulus", 1.0)
    # Avoid zero division
    elastic_safe = np.where(elastic == 0.0, 1e-5, elastic)
    df_derived["stiffness_ratio"] = tensile / elastic_safe

    return df_derived
