"""Data pipeline: Validation -> Cleaning -> Normalization -> Feature Engineering -> Training Dataset."""

import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List
from sklearn.preprocessing import StandardScaler
from shared.ml.config import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

def validate_raw_dataset(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Audit raw DataFrame schema and essential columns."""
    errors = []
    if df.empty:
        errors.append("Dataset is empty.")
        return False, errors

    required = ["polymer", "category"]
    for col in required:
        if col not in df.columns:
            errors.append(f"Missing essential column: {col}")

    # Check that at least some feature columns exist
    found_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    if len(found_features) < 3:
        errors.append(f"Too few feature columns found ({len(found_features)}/15).")

    return len(errors) == 0, errors

def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data: handle missing values, types, and range bounds."""
    df_clean = df.copy()

    # Coerce numeric columns
    for col in FEATURE_COLUMNS:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    # Fill median for numeric features if missing
    for col in FEATURE_COLUMNS:
        if col in df_clean.columns and df_clean[col].isnull().any():
            median_val = df_clean[col].median()
            df_clean[col] = df_clean[col].fillna(median_val if not pd.isna(median_val) else 0.0)

    # Physical bounds enforcement
    if "biocompatibility" in df_clean.columns:
        df_clean["biocompatibility"] = df_clean["biocompatibility"].clip(0.0, 10.0)
    if "toxicity_score" in df_clean.columns:
        df_clean["toxicity_score"] = df_clean["toxicity_score"].clip(0.0, 10.0)
    if "biodegradation_days" in df_clean.columns:
        df_clean["biodegradation_days"] = df_clean["biodegradation_days"].clip(0.0, 10000.0)

    return df_clean

def normalize_features(
    df: pd.DataFrame,
    scaler: StandardScaler = None,
    fit: bool = True,
) -> Tuple[np.ndarray, StandardScaler]:
    """Apply standard scaling normalization to feature matrix."""
    X = df[FEATURE_COLUMNS].values.astype(np.float32)
    if fit or scaler is None:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = scaler.transform(X)
    return X_scaled, scaler

def prepare_training_dataset(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, StandardScaler, Dict[str, Any]]:
    """Complete data pipeline execution."""
    is_valid, errors = validate_raw_dataset(df_raw)
    if not is_valid:
        raise ValueError(f"Dataset validation failed: {errors}")

    df_clean = clean_dataset(df_raw)

    # Convert suitability_label to binary integer (0 or 1) for classification algorithms
    if "suitability_label" in df_clean.columns:
        df_clean["suitability_label"] = (
            pd.to_numeric(df_clean["suitability_label"], errors="coerce").fillna(0.0) >= 0.5
        ).astype(int)
    else:
        # Synthesize binary suitability_label if not present
        biocompat = df_clean.get("biocompatibility", 5.0)
        toxicity = df_clean.get("toxicity_score", 5.0)
        tensile = df_clean.get("tensile_strength", 20.0)
        df_clean["suitability_label"] = (
            (biocompat >= 4.0) & (toxicity >= 3.0) & (tensile >= 5.0)
        ).astype(int)

    _, scaler = normalize_features(df_clean, fit=True)

    metadata = {
        "total_rows": len(df_clean),
        "feature_count": len(FEATURE_COLUMNS),
        "positive_labels": int(df_clean["suitability_label"].sum()),
        "negative_labels": int((df_clean["suitability_label"] == 0).sum()),
    }

    return df_clean, scaler, metadata
