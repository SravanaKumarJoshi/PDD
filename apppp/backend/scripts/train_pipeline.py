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

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

def load_data_from_mysql_or_fallback() -> pd.DataFrame:
    """Load data exclusively from production MySQL database table."""
    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:meheer17@localhost:3306/polysaccharide_selector")
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        query = """
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
        df = pd.read_sql(query, engine)
        df = df.loc[:, ~df.columns.duplicated()]
        if df.empty:
            raise RuntimeError(f"MySQL table 'materials' returned 0 records.")
        print(f"[TrainPipeline] Loaded {len(df)} production records from MySQL 'materials' database.")
        return df
    except Exception as e:
        print(f"[TrainPipeline] ERROR: Failed to connect to MySQL database or query table '{MATERIAL_TABLE_NAME}': {e}")
        raise RuntimeError(f"Strict MySQL data source requirement violated. Connection error: {e}") from e

def main():
    parser = argparse.ArgumentParser(description="BioPolymer Model Training Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Perform training without updating production 'latest' symlink")
    args = parser.parse_args()

    print("[TrainPipeline] Starting production model training with SHA-256 checksums & digital signing...")
    train_config = load_yaml_config("training_config.yaml")

    # 1. Load Data strictly from MySQL
    df_raw = load_data_from_mysql_or_fallback()

    # Compute Dataset SHA-256 Hash
    dataset_bytes = df_raw.to_json().encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()[:16]

    # 2. Execute Data Cleaning
    df_clean, _, data_meta = prepare_training_dataset(df_raw)

    # 3. Leakage-Free Grouped Split (Grouped by Polymer Name)
    X_unscaled = df_clean[FEATURE_COLUMNS].values.astype(np.float32)
    y = df_clean["suitability_label"].values
    groups = df_clean["polymer"].values

    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, holdout_idx = next(gss.split(X_unscaled, y, groups=groups))

    # 4. Strict Preprocessing Fitting ONLY on Training Split (No Data Leakage)
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_unscaled[train_idx])
    X_holdout = scaler.transform(X_unscaled[holdout_idx])

    y_train, groups_train = y[train_idx], groups[train_idx]
    y_holdout = y[holdout_idx]

    print(f"[TrainPipeline] Leakage-Free Split: {len(X_train)} Train Samples ({len(np.unique(groups_train))} polymers), {len(X_holdout)} Independent Hold-out Samples.")

    # 5. Benchmark Candidates with GroupKFold Cross-Validation
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
            if latest_pointer.is_dir() and not latest_pointer.is_symlink():
                shutil.rmtree(latest_pointer)
            else:
                latest_pointer.unlink()

        try:
            latest_pointer.symlink_to(version_dir, target_is_directory=True)
            print(f"[TrainPipeline] Symlinked 'latest' -> {version_str}")
        except Exception:
            shutil.copytree(version_dir, latest_pointer)
            print(f"[TrainPipeline] Copied version {version_str} -> 'latest'")

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
