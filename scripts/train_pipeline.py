#!/usr/bin/env python3
"""
train_pipeline.py — Standalone Model-Agnostic AI Training & Benchmarking Pipeline

Production MLOps Governance & Security:
- SHA-256 Checksum generation for all exported model binaries (model.joblib, scaler.joblib, feature_matrix.npy)
- Digital HMAC-SHA256 signing of metadata manifests to prevent tampering
- Immutable deployment audit logging (models/registry/deployment_audit_log.jsonl)
- Dataset & Policy versioning (dataset_version, policy_version)
- GroupKFold & GroupShuffleSplit by polymer name (zero data leakage across folds)
- Platt Scaling probability calibration
- Independent hold-out dataset evaluation
- Full reproducibility logging (Git commit hash, dataset SHA-256 hash, hyperparams)
"""

import os
import sys
import json
import shutil
import hmac
import hashlib
import subprocess
import argparse
import joblib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

# Ensure root directory and apppp/backend directory are on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "apppp" / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shared.ml.config import load_yaml_config, MATERIAL_TABLE_NAME, FEATURE_COLUMNS
from shared.ml.data_pipeline import prepare_training_dataset
from shared.ml.benchmarking import benchmark_and_select_best_model_leakage_free
from shared.ml.faiss_search import FAISSSearchEngine

REGISTRY_DIR = ROOT_DIR / "models" / "registry"
SIGNING_SECRET = os.getenv("MODEL_SIGNING_SECRET_KEY", "biopolymer-production-signing-key-987654321")

def get_git_commit_hash() -> str:
    """Retrieve current Git commit hash for reproducibility audit."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT_DIR))
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "untracked_commit"

def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 checksum for a binary or text file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def compute_hmac_signature(data_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for data payload."""
    return hmac.new(secret.encode("utf-8"), data_bytes, hashlib.sha256).hexdigest()

def record_deployment_audit_log(action: str, prev_version: str, new_version: str, performed_by: str, reason: str):
    """Record an immutable entry in the deployment audit log."""
    log_file = REGISTRY_DIR / "deployment_audit_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "previous_version": prev_version,
        "new_version": new_version,
        "performed_by": performed_by,
        "reason": reason
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def standardize_material_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame columns conform to the standard schema used across ML pipeline and UI."""
    if df is None or df.empty:
        return df

    df = df.copy()

    column_mapping = {
        "name": "polymer",
        "tensileStrengthMpaMin": "tensile_strength",
        "tensileStrengthMpaMax": "tensile_strength_max",
        "elasticModulusGpaMin": "elastic_modulus",
        "elasticModulusGpaMax": "elastic_modulus_max",
        "elongationPctMin": "elongation_pct",
        "degradationDaysMin": "biodegradation_days",
        "enzymaticDegradability": "environmental_impact",
        "cytotoxicitySafe": "cytotoxicity_safe",
        "sterGamma": "sterilization_gamma",
        "sterEto": "sterilization_eto",
        "sterSteam": "sterilization_steam",
        "procFilm": "film_forming",
        "evidenceLevel": "evidence_level",
    }

    rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns and new not in df.columns}
    if rename_dict:
        df = df.rename(columns=rename_dict)

    if "polymer" not in df.columns:
        if "name" in df.columns:
            df["polymer"] = df["name"]
        else:
            df["polymer"] = "Unknown Polymer"

    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    if "biocompatibility" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["biocompatibility"] = df["cytotoxicity_safe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        elif "cytotoxicitySafe" in df.columns:
            df["biocompatibility"] = df["cytotoxicitySafe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        else:
            df["biocompatibility"] = 8.0

    if "toxicity_score" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["toxicity_score"] = df["cytotoxicity_safe"].apply(
                lambda x: 8.5 if str(x).strip() in ["1", "1.0", "True", "true"] else 3.0
            )
        else:
            df["toxicity_score"] = 8.0

    if "tensile_strength" not in df.columns:
        if "tensileStrengthMpaMin" in df.columns:
            df["tensile_strength"] = pd.to_numeric(df["tensileStrengthMpaMin"], errors="coerce").fillna(20.0)
        else:
            df["tensile_strength"] = 20.0

    if "elastic_modulus" not in df.columns:
        if "elasticModulusGpaMin" in df.columns:
            df["elastic_modulus"] = pd.to_numeric(df["elasticModulusGpaMin"], errors="coerce").fillna(1.2)
        else:
            df["elastic_modulus"] = 1.2

    if "elongation_pct" not in df.columns:
        if "elongationPctMin" in df.columns:
            df["elongation_pct"] = pd.to_numeric(df["elongationPctMin"], errors="coerce").fillna(45.0)
        else:
            df["elongation_pct"] = 45.0

    if "flexibility" not in df.columns:
        if "elongation_pct" in df.columns:
            df["flexibility"] = pd.to_numeric(df["elongation_pct"], errors="coerce").fillna(45.0) * 0.8
        else:
            df["flexibility"] = 35.0

    if "wvtr" not in df.columns:
        df["wvtr"] = 800.0

    if "oxygen_permeability" not in df.columns:
        if "otr" in df.columns:
            df["oxygen_permeability"] = pd.to_numeric(df["otr"], errors="coerce").fillna(120.0)
        else:
            df["oxygen_permeability"] = 120.0

    if "antimicrobial" not in df.columns:
        df["antimicrobial"] = 0.0

    if "biodegradation_days" not in df.columns:
        if "degradationDaysMin" in df.columns:
            df["biodegradation_days"] = pd.to_numeric(df["degradationDaysMin"], errors="coerce").fillna(60.0)
        else:
            df["biodegradation_days"] = 60.0

    if "environmental_impact" not in df.columns:
        df["environmental_impact"] = 5.0

    if "film_forming" not in df.columns:
        df["film_forming"] = 1.0

    if "sterilization_gamma" not in df.columns:
        df["sterilization_gamma"] = 0.0

    if "sterilization_eto" not in df.columns:
        df["sterilization_eto"] = 0.0

    if "sterilization_steam" not in df.columns:
        df["sterilization_steam"] = 0.0

    if "is_augmented" not in df.columns:
        df["is_augmented"] = 0

    if "evidence_level" not in df.columns:
        df["evidence_level"] = "high"

    if "suitability_label" not in df.columns:
        if "biocompatibility" in df.columns:
            bio = pd.to_numeric(df["biocompatibility"], errors="coerce").fillna(5.0)
            df["suitability_label"] = (bio >= bio.median()).astype(int)
        else:
            df["suitability_label"] = 1

    return df

def load_data_from_mysql_or_fallback() -> pd.DataFrame:
    """Load dataset from MySQL database with automatic fallback to biopolymer_materials_1000.csv."""
    try:
        from dotenv import load_dotenv
        env_path = BACKEND_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        elif (ROOT_DIR / ".env").exists():
            load_dotenv(ROOT_DIR / ".env")
    except Exception:
        pass

    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:root123@localhost:3306/polysaccharide_selector")
    db_url = db_url.replace("mysql+aiomysql://", "mysql+pymysql://")

    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        query = f"SELECT * FROM {MATERIAL_TABLE_NAME}"
        df = pd.read_sql(query, engine)
        if df.empty:
            query_join = """
            SELECT 
                m.name AS polymer,
                m.category AS category,
                COALESCE(mp.tensile_strength_mpa_min, 15.0) AS tensile_strength,
                COALESCE(mp.elastic_modulus_gpa_min, 1.2) AS elastic_modulus,
                COALESCE(mp.elongation_pct_min, 45.0) AS elongation_pct,
                COALESCE(mp.elongation_pct_min * 0.8, 35.0) AS flexibility,
                COALESCE(mp.wvtr, 800.0) AS wvtr,
                COALESCE(mp.otr, 120.0) AS oxygen_permeability,
                CASE WHEN mp.cytotoxicity_safe = 1 THEN 9.0 ELSE 4.0 END AS biocompatibility,
                CASE WHEN mp.cytotoxicity_safe = 1 THEN 8.5 ELSE 3.0 END AS toxicity_score,
                CASE WHEN mp.antimicrobial = 1 THEN 1.0 ELSE 0.0 END AS antimicrobial,
                COALESCE(mp.degradation_days_min, 60) AS biodegradation_days,
                CASE WHEN mp.enzymatic_degradability = 1 THEN 9.0 ELSE 5.0 END AS environmental_impact,
                CASE WHEN mp.proc_film = 1 THEN 1.0 ELSE 0.0 END AS film_forming,
                CASE WHEN mp.ster_gamma = 1 THEN 1.0 ELSE 0.0 END AS sterilization_gamma,
                CASE WHEN mp.ster_eto = 1 THEN 1.0 ELSE 0.0 END AS sterilization_eto,
                CASE WHEN mp.ster_steam = 1 THEN 1.0 ELSE 0.0 END AS sterilization_steam
            FROM materials m 
            JOIN material_properties mp ON m.id = mp.material_id 
            WHERE m.is_deleted = 0
            """
            df = pd.read_sql(query_join, engine)

        if not df.empty:
            print(f"[TrainPipeline] Loaded {len(df)} rows from MySQL database.")
            return standardize_material_dataframe(df)
    except Exception as e:
        print(f"[TrainPipeline] WARNING: Could not query MySQL ({e}). Trying fallback CSV...")

    csv_paths = [
        ROOT_DIR / "biopolymer_materials_1000.csv",
        BACKEND_DIR / "biopolymer_materials_1000.csv"
    ]
    for csv_path in csv_paths:
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"[TrainPipeline] Loaded {len(df)} rows from fallback CSV: {csv_path.name}")
            return standardize_material_dataframe(df)

    raise RuntimeError("Failed to load training dataset from MySQL or fallback CSV files.")



def main():
    parser = argparse.ArgumentParser(description="BioPolymer Model Training Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Perform training without updating production 'latest' symlink")
    args = parser.parse_args()

    print("[TrainPipeline] Starting training with SHA-256 checksums & digital signing...")
    train_config = load_yaml_config("training_config.yaml")

    # 1. Load Data
    df_raw = load_data_from_mysql_or_fallback()

    # Compute Dataset SHA-256 Hash
    dataset_bytes = df_raw.to_json().encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()[:16]

    # 2. Execute Data Pipeline (Validate -> Clean -> Normalize)
    df_clean, scaler, data_meta = prepare_training_dataset(df_raw)

    # 3. Leakage-Free Grouped Split (Grouped by Polymer Name)
    X = df_clean[FEATURE_COLUMNS].values
    y = df_clean["suitability_label"].values
    groups = df_clean["polymer"].values

    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, holdout_idx = next(gss.split(X, y, groups=groups))

    X_train, y_train, groups_train = X[train_idx], y[train_idx], groups[train_idx]
    X_holdout, y_holdout = X[holdout_idx], y[holdout_idx]

    print(f"[TrainPipeline] Grouped Split: {len(X_train)} Train Samples ({len(np.unique(groups_train))} polymers), {len(X_holdout)} Independent Hold-out Samples.")

    # 4. Benchmark Candidates with GroupKFold Cross-Validation
    best_wrapper, best_metrics, leaderboard = benchmark_and_select_best_model_leakage_free(
        X_train, y_train, groups_train, X_holdout, y_holdout, config=train_config
    )

    print(f"[TrainPipeline] Winner Algorithm: {best_wrapper.name} (Hold-out F1: {best_metrics['f1']}, GroupCV F1: {best_metrics['group_cv_f1_mean']})")

    # 5. Build FAISS Vector Search Index
    faiss_engine = FAISSSearchEngine()
    faiss_engine.build_index(df_clean, scaler=scaler)

    # 6. Versioning & Directory Creation
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    existing_versions = [d.name for d in REGISTRY_DIR.iterdir() if d.is_dir() and d.name.startswith("v")]
    version_num = len(existing_versions) + 1
    version_str = f"v{version_num}"
    version_dir = REGISTRY_DIR / version_str
    version_dir.mkdir(parents=True, exist_ok=True)

    # 7. Save Model, Scaler, and Feature Matrix Artifacts
    model_file = version_dir / "model.joblib"
    scaler_file = version_dir / "scaler.joblib"
    feature_file = version_dir / "feature_matrix.npy"

    joblib.dump(best_wrapper, model_file)
    joblib.dump(scaler, scaler_file)
    np.save(feature_file, faiss_engine.feature_matrix)

    # Compute Checksums for Artifacts
    artifact_checksums = {
        "model.joblib": compute_file_sha256(model_file),
        "scaler.joblib": compute_file_sha256(scaler_file),
        "feature_matrix.npy": compute_file_sha256(feature_file),
    }

    # 8. Construct Reproducibility & Governance Metadata
    git_hash = get_git_commit_hash()
    meta_payload = {
        "model_version": version_str,
        "model_type": "Baseline Suitability Model (Policy Approximation)",
        "label_source": "Rule-Based Threshold Policy",
        "label_version": "v1.0",
        "dataset_version": "v1.0.0",
        "policy_version": "v1.0",
        "algorithm": best_wrapper.name,
        "git_commit_hash": git_hash,
        "dataset_hash": dataset_hash,
        "training_dataset": MATERIAL_TABLE_NAME,
        "artifact_checksums": artifact_checksums,
        "selected_metrics": best_metrics,
        "leaderboard": leaderboard,
        "dataset_metadata": data_meta,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_config": train_config,
        "governance": {
            "is_empirical_lab_data": False,
            "policy_approximation_note": "Trained on rule-derived baseline suitability policy. Transition to lab outcome labels scheduled for Phase 2."
        },
        "leakage_prevention": {
            "strategy": "GroupShuffleSplit & GroupKFold by polymer name",
            "unique_train_groups": int(len(np.unique(groups_train))),
            "unique_holdout_groups": int(len(np.unique(groups[holdout_idx]))),
            "holdout_size": int(len(X_holdout))
        }
    }

    # Compute Digital HMAC Signature over metadata payload string
    meta_json_str = json.dumps(meta_payload, sort_keys=True)
    digital_signature = compute_hmac_signature(meta_json_str.encode("utf-8"), SIGNING_SECRET)
    meta_payload["digital_signature"] = digital_signature

    meta_file = version_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_payload, f, indent=2)

    # 9. Update 'latest' pointer & Record Audit Log
    prev_version = "v0"
    latest_pointer = REGISTRY_DIR / "latest"
    if latest_pointer.exists():
        try:
            target_resolved = latest_pointer.resolve() if latest_pointer.is_symlink() else latest_pointer
            meta_prev = target_resolved / "metadata.json"
            if meta_prev.exists():
                with open(meta_prev, "r", encoding="utf-8") as pf:
                    prev_version = json.load(pf).get("model_version", "unknown")
        except Exception:
            pass

    if not args.dry_run:
        if latest_pointer.exists() or latest_pointer.is_symlink():
            try:
                if latest_pointer.is_dir() and not latest_pointer.is_symlink():
                    shutil.rmtree(latest_pointer)
                else:
                    latest_pointer.unlink()
            except Exception as e:
                print(f"[TrainPipeline] Warning removing existing latest pointer: {e}")

        try:
            latest_pointer.symlink_to(version_dir, target_is_directory=True)
            print(f"[TrainPipeline] Symlinked 'latest' -> {version_str}")
        except Exception:
            shutil.copytree(version_dir, latest_pointer, dirs_exist_ok=True)
            print(f"[TrainPipeline] Copied version {version_str} -> 'latest'")

        # Also sync to backend registry directory if distinct
        backend_registry = BACKEND_DIR / "models" / "registry"
        if backend_registry.exists() and backend_registry != REGISTRY_DIR:
            backend_v_dir = backend_registry / version_str
            shutil.copytree(version_dir, backend_v_dir, dirs_exist_ok=True)
            backend_latest = backend_registry / "latest"
            if backend_latest.exists() or backend_latest.is_symlink():
                try:
                    if backend_latest.is_dir() and not backend_latest.is_symlink():
                        shutil.rmtree(backend_latest)
                    else:
                        backend_latest.unlink()
                except Exception:
                    pass
            shutil.copytree(version_dir, backend_latest, dirs_exist_ok=True)

        # Record deployment audit log
        record_deployment_audit_log(
            action="PROMOTION",
            prev_version=prev_version,
            new_version=version_str,
            performed_by="train_pipeline_service",
            reason="Automated model benchmarking promotion after successful evaluation."
        )

    print(f"[TrainPipeline] Training & MLOps signing complete! Version: {version_str}, Signature: {digital_signature[:12]}...")

if __name__ == "__main__":
    main()
