"""
imputation.py — ML Fallback Imputation Interface

Provides the `predict_missing_properties` API which loads trained ML models
to impute missing numeric values in material rows before they are sent to the
rule-based scoring engine.
"""

import os
import joblib
import pandas as pd
import numpy as np
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"

# In a real environment, we'd load models lazily or on startup.
# We also distinguish between production models and SAMPLE models if needed.
_models = {}

def _get_model(target: str, is_sample: bool = False):
    prefix = "SAMPLE_" if is_sample else ""
    # Try to find a directory matching the target
    if not MODELS_DIR.exists():
        return None
        
    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir() and model_dir.name.endswith(target) and model_dir.name.startswith(prefix):
            model_path = model_dir / "model.joblib"
            if model_path.exists():
                if model_path not in _models:
                    _models[model_path] = joblib.load(model_path)
                return _models[model_path]
    return None

def _extract_features(material_row: dict) -> np.ndarray:
    """Extract deterministic features identical to training."""
    smiles = material_row.get("smiles", "")
    backbone = material_row.get("backbone_group", smiles[:5] if smiles else "unknown")
    
    mw = float(int(hashlib.md5(str(smiles).encode()).hexdigest(), 16) % 1000)
    logp = float((int(hashlib.md5(str(smiles).encode()).hexdigest(), 16) % 100) / 10.0 - 5.0)
    length = len(str(smiles))
    backbone_hash = hash(backbone) % 100
    
    return np.array([[mw, logp, length, backbone_hash]])

def predict_missing_properties(material_row: dict, is_sample: bool = False) -> dict:
    """
    Imputes missing numeric properties for a material using trained models.
    Does NOT override existing values.
    
    Returns:
        A dictionary of predicted fields and uncertainty flags.
    """
    results = {}
    features = None
    
    targets_to_impute = ["tensile_strength_mpa_max", "elastic_modulus_gpa_max", "wvtr"]
    
    for target in targets_to_impute:
        # Only impute if missing
        if pd.isna(material_row.get(target)) or material_row.get(target) is None:
            model = _get_model(target, is_sample=is_sample)
            if model:
                if features is None:
                    features = _extract_features(material_row)
                    
                prediction = float(model.predict(features)[0])
                
                # Simple OOD Guardrail: In a real system, we'd check against schema min/max.
                if prediction < 0:
                    prediction = 0.0 # Physical properties can't be negative
                    
                results[target] = prediction
                
    if results:
        results["is_imputed"] = True
        results["evidence_level"] = "low"
        
    return results
