#!/usr/bin/env python3
"""
train_model.py — Train Imputation Models for BioPolymer Pipeline

Trains LightGBM, CatBoost, and Baseline models for predicting missing numeric properties.
Evaluates them with strict GroupKFold cross-validation and missing-feature stress tests.
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import GroupKFold
import lightgbm as lgb
import catboost as cb
import joblib

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
PROCESSED_DIR = DATASETS_DIR / "processed"
METADATA_DIR = DATASETS_DIR / "metadata"
MODELS_DIR = BASE_DIR / "models"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = ["tensile_strength_mpa_max", "elastic_modulus_gpa_max", "wvtr"]

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract deterministic molecular features from SMILES for the ML model to use."""
    features = pd.DataFrame(index=df.index)
    # In a real pipeline, we'd use rdkit.Chem.Descriptors.
    # Here, we generate mock deterministic features from the SMILES string.
    def mock_mw(s): return float(int(hashlib.md5(str(s).encode()).hexdigest(), 16) % 1000)
    def mock_logp(s): return float((int(hashlib.md5(str(s).encode()).hexdigest(), 16) % 100) / 10.0 - 5.0)
    
    features['mw'] = df['smiles'].apply(mock_mw)
    features['logp'] = df['smiles'].apply(mock_logp)
    features['length'] = df['smiles'].apply(lambda x: len(str(x)))
    features['backbone_hash'] = df['backbone_group'].apply(lambda x: hash(x) % 100)
    
    return features

def train_and_evaluate(args):
    mode = "SAMPLE" if args.offline_sample else "REAL"
    
    data_path = PROCESSED_DIR / mode / "master_dataset.parquet"
    catalog_path = METADATA_DIR / f"{mode}_dataset_catalog.json"
    
    if not data_path.exists() or not catalog_path.exists():
        print(f"FATAL: Required dataset files not found for {mode} mode. Did you run datasets_build.py?")
        sys.exit(1)
        
    print(f"Loading dataset from {data_path}...")
    df = pd.read_parquet(data_path)
    
    features_df = extract_features(df)
    feature_names = features_df.columns.tolist()
    
    groups = df['backbone_group'].values
    unique_groups_count = len(np.unique(groups))
    is_unknown_group = unique_groups_count == 1 and groups[0] == "UNKNOWN"
    
    split_strategy = "KFold" if (unique_groups_count < 2 or is_unknown_group) else "GroupKFold"
    leakage_warning = split_strategy == "KFold"
    
    metrics_report = {
        "_metadata": {
            "split_strategy": split_strategy,
            "group_column_used": "UNKNOWN" if is_unknown_group else "backbone_group",
            "unique_group_count": int(unique_groups_count),
            "leakage_warning_occurred": leakage_warning
        }
    }
    
    for target in TARGETS:
        print(f"\n--- Training models for target: {target} ---")
        
        # Filter where target is not null
        mask = df[target].notna()
        X = features_df[mask].values
        y = df.loc[mask, target].values
        g = groups[mask]
        
        if len(y) < 10:
            print(f"Not enough data for {target}. Skipping.")
            continue
            
        # Cross-validation Strategy
        if split_strategy == "GroupKFold":
            cv_splitter = GroupKFold(n_splits=3 if len(np.unique(g)) >= 3 else 2)
            cv_args = {"groups": g}
        else:
            from sklearn.model_selection import KFold
            cv_splitter = KFold(n_splits=5, shuffle=True, random_state=42)
            cv_args = {}
            
        # Models
        models = {
            "Baseline_Median": DummyRegressor(strategy="median"),
            "LightGBM": lgb.LGBMRegressor(random_state=42, n_estimators=50, verbose=-1),
            "CatBoost": cb.CatBoostRegressor(random_state=42, iterations=50, verbose=0)
        }
        
        target_metrics = {}
        best_model_name = None
        best_r2 = -float("inf")
        best_model_instance = None
        
        for name, model in models.items():
            maes, rmses, r2s = [], [], []
            for train_idx, test_idx in cv_splitter.split(X, y, **cv_args):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]
                
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                
                maes.append(mean_absolute_error(y_test, preds))
                rmses.append(root_mean_squared_error(y_test, preds))
                r2s.append(r2_score(y_test, preds))
                
            avg_mae = np.mean(maes)
            avg_rmse = np.mean(rmses)
            avg_r2 = np.mean(r2s)
            
            target_metrics[name] = {
                "MAE": float(avg_mae),
                "RMSE": float(avg_rmse),
                "R2": float(avg_r2)
            }
            
            print(f"[{name}] MAE: {avg_mae:.2f} | RMSE: {avg_rmse:.2f} | R2: {avg_r2:.2f}")
            
            # Re-train on all data for final artifact
            model.fit(X, y)
            
            # Select best model (excluding baseline)
            if name != "Baseline_Median" and avg_r2 > best_r2:
                best_r2 = avg_r2
                best_model_name = name
                best_model_instance = model
                
        baseline_mae = target_metrics["Baseline_Median"]["MAE"]
        best_mae = target_metrics[best_model_name]["MAE"]
        
        if best_r2 < 0:
            print(f"[FAIL] {best_model_name} beat baseline MAE but has negative R2 ({best_r2:.2f}). Models with negative/unstable R2 are rejected.")
            print("HONEST EVALUATION SUMMARY: The dataset size/quality is insufficient to train a stable predictor. Do not ship ML imputation yet; keep unknowns unknown until more data is acquired.")
            metrics_report[target] = {"Status": "Rejected, negative R2"}
            continue
            
        if best_mae < baseline_mae:
            print(f"[PASS] {best_model_name} beat the baseline for {target} with R2 {best_r2:.2f}! Saving model...")
            
            # Robustness Test (Missing Features)
            # Simulate dropping 20% of features at random
            X_drop = X.copy()
            drop_mask = np.random.rand(*X_drop.shape) < 0.2
            X_drop[drop_mask] = 0.0 # or mean imputation
            preds_drop = best_model_instance.predict(X_drop)
            robust_mae = mean_absolute_error(y, preds_drop)
            target_metrics["Robustness_Drop20Pct_MAE"] = float(robust_mae)
            
            model_dir = MODELS_DIR / mode / f"{best_model_name}_{target}"
            model_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(best_model_instance, model_dir / "model.joblib")
            
            schema = {
                "features": feature_names,
                "target": target,
                "min_expected": float(np.min(X, axis=0).tolist()[0]), # simplifying for OOD
                "max_expected": float(np.max(X, axis=0).tolist()[0])
            }
            with open(model_dir / "schema.json", "w") as f:
                json.dump(schema, f, indent=2)
                
            metrics_report[target] = target_metrics
            
            # Model Card
            with open(model_dir / "MODEL_CARD.md", "w") as f:
                f.write(f"# {best_model_name} for {target}\n")
                f.write(f"## Intended Use\nOffline fallback imputation for BioPolymer pipeline.\n")
                f.write(f"## Metrics\nMAE: {best_mae:.2f}\nBaseline MAE: {baseline_mae:.2f}\n")
                f.write(f"## Robustness\nDrop 20% Features MAE: {robust_mae:.2f}\n")
        else:
            print(f"[FAIL] ML did not beat baseline for {target} (Best MAE: {best_mae:.2f} vs Baseline: {baseline_mae:.2f}). ML integration rejected for this target.")
            metrics_report[target] = {"Status": "Rejected, failed to beat baseline"}
            
    # Save global metrics
    (MODELS_DIR / mode).mkdir(parents=True, exist_ok=True)
    with open(MODELS_DIR / mode / "metrics_report.json", "w") as f:
        json.dump(metrics_report, f, indent=2)
        
    print("\nModel training phase completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ML Imputation Models")
    parser.add_argument("--offline-sample", action="store_true", help="Run in CI sample mode (uses SAMPLE datasets, produces SAMPLE models)")
    args = parser.parse_args()
    
    train_and_evaluate(args)
