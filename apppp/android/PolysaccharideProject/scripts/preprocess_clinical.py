import os
import pandas as pd
import numpy as np
import json
import hashlib
import time
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

# --- CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_All")
PROC_DIR = os.path.join(BASE_DIR, "datasets", "processed")
META_DIR = os.path.join(BASE_DIR, "datasets", "metadata")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
CATALOG_PATH = os.path.join(META_DIR, "dataset_catalog.json")

RANDOM_SEED = 42
REQUIRED_FEATURES = ["mw_kda", "source_origin", "monomer_unit", "bond_type"]
# source_origin maps to 'source' in raw, monomer_unit to 'monomer', bond_type to 'bond'
SCHEMA_MAPPING = {
    "mw_kda": "mw_kda",
    "source": "source_origin",
    "monomer": "monomer_unit",
    "bond": "bond_type",
    "solubility": "solubility"
}

BLOCKED_FEATURES = ["name", "id", "scientific_name", "common_name", "dataset_id", "filename"]
TARGET_LABEL = "category"

def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def load_and_verify():
    if not os.path.exists(CATALOG_PATH):
        raise FileNotFoundError(f"Catalog missing at {CATALOG_PATH}. Run download_datasets.py first.")

    with open(CATALOG_PATH, "r") as f:
        catalog = json.load(f)

    verified_files = []
    for entry in catalog:
        fpath = os.path.abspath(entry["local_path"])
        if not fpath.startswith(os.path.abspath(RAW_DIR)):
            raise ValueError(f"SECURITY ALERT: Raw file {fpath} is outside the allowed raw folder.")
        if not os.path.exists(fpath):
            print(f"Warning: Referenced file {fpath} not found on disk.")
            continue
        verified_files.append((entry, fpath))

    return verified_files

def run_leakage_audit(df, blocked_in_df):
    print("Running Leakage Audit (RF3)...")
    if not blocked_in_df:
        return {"passed": True, "metrics": {}, "note": "No blocked features found in data."}

    audit_df = df[blocked_in_df + [TARGET_LABEL]].copy()
    # Basic encoding for audit
    for col in audit_df.columns:
        audit_df[col] = LabelEncoder().fit_transform(audit_df[col].astype(str))

    X = audit_df[blocked_in_df]
    y = audit_df[TARGET_LABEL]

    num_classes = len(np.unique(y))
    chance_level = 1.0 / num_classes
    threshold = chance_level + 0.10

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=RANDOM_SEED)

    probes = {
        "DecisionTree": DecisionTreeClassifier(random_state=RANDOM_SEED),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=RANDOM_SEED),
        "RandomForest": RandomForestClassifier(n_estimators=50, random_state=RANDOM_SEED)
    }

    metrics = {}
    audit_passed = True
    leaky_fields = []

    for name, model in probes.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='macro')
        metrics[name] = {"accuracy": acc, "macro_f1": f1}

        if acc > threshold or f1 > threshold:
            audit_passed = False
            leaky_fields.append(name)

    return {
        "passed": audit_passed,
        "metrics": metrics,
        "threshold": threshold,
        "chance_level": chance_level,
        "blocked_features_used": blocked_in_df
    }

def main():
    os.makedirs(PROC_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    start_time = time.time()
    verified = load_and_verify()

    all_data = []
    raw_files_metadata = []

    for entry, path in verified:
        raw_files_metadata.append({
            "filename": entry["filename"],
            "sha256": compute_sha256(path)
        })

        # Load data (only CSV supported for now in this dense phase)
        if entry["filename"].endswith(".csv"):
            df = pd.read_csv(path)
            # Map columns to dense schema
            df = df.rename(columns=SCHEMA_MAPPING)
            # Add provenance
            df["dataset_id"] = entry["id"]
            df["filename"] = entry["filename"]
            all_data.append(df)

    if not all_data:
        raise ValueError("No data loaded. Preprocessing failed.")

    master_df = pd.concat(all_data, axis=0, ignore_index=True)
    total_loaded = len(master_df)

    # 1. Drop duplicates
    master_df = master_df.drop_duplicates()
    dropped_duplicates = total_loaded - len(master_df)

    # 2. Missingness Enforcement
    # Normalize features names
    available_required = [f for f in REQUIRED_FEATURES if f in master_df.columns]

    def calculate_missing_rate(row):
        missing = 0
        for f in available_required:
            val = row.get(f)
            if pd.isna(val) or val == "Unknown":
                missing += 1
        return missing / len(REQUIRED_FEATURES)

    master_df["required_missing_rate"] = master_df.apply(calculate_missing_rate, axis=1)
    final_df = master_df[master_df["required_missing_rate"] <= 0.40].copy()
    dropped_missing = len(master_df) - len(final_df)

    # Check minimum rows per class
    counts = final_df[TARGET_LABEL].value_counts()
    if any(counts < 20):
        print(f"Warning: Some classes have low representation: \n{counts}")

    # 3. Leakage Audit
    blocked_in_df = [f for f in BLOCKED_FEATURES if f in final_df.columns]
    audit_results = run_leakage_audit(final_df, blocked_in_df)

    if not audit_results["passed"]:
        print("CRITICAL: Leakage Audit Failed! One or more blocked features predict the target label.")
        # We continue to generate the report but this will set valid=false later

    # 4. Final Dataset Cleanup
    # Ensure dense schema columns exist
    final_cols = REQUIRED_FEATURES + ["solubility", TARGET_LABEL, "dataset_id"]
    for col in final_cols:
        if col not in final_df.columns:
            final_df[col] = "Unknown"

    # Save processed data
    processed_path = os.path.join(PROC_DIR, "master_clinical_dataset.csv")
    final_df[final_cols].to_csv(processed_path, index=False)
    processed_hash = compute_sha256(processed_path)

    # 5. Quality Report
    quality_report = {
        "run_timestamp": str(datetime.now()),
        "random_seed": RANDOM_SEED,
        "raw_files_used": raw_files_metadata,
        "schema_fields": final_cols,
        "row_counts": {
            "total_loaded": total_loaded,
            "dropped_duplicates": dropped_duplicates,
            "dropped_missing_required": dropped_missing,
            "final_rows": len(final_df)
        },
        "missingness": {
            "per_feature_missing_rate": (final_df[final_cols] == "Unknown").mean().to_dict()
        },
        "label_distribution": final_df[TARGET_LABEL].value_counts().to_dict(),
        "leakage_audit": audit_results,
        "processed_file_hash": processed_hash,
        "leakage_audit_passed": audit_results["passed"]
    }

    report_path = os.path.join(META_DIR, "data_quality_report.json")
    with open(report_path, "w") as f:
        json.dump(quality_report, f, indent=4)

    # 6. Summary Markdown
    summary_md = f"""# Preprocessing Summary

## Dataset Metrics
- Total Loaded: {total_loaded}
- Dropped (Duplicates): {dropped_duplicates}
- Dropped (High Missingness >40%): {dropped_missing}
- Final Row Count: {len(final_df)}

## Schema Integrity
- Required Features: {', '.join(REQUIRED_FEATURES)}
- Target Label: {TARGET_LABEL}

## Leakage Audit
- Passed: {"✅ YES" if audit_results["passed"] else "❌ NO"}
- Blocked Features Used: {', '.join(blocked_in_df)}
- Threshold: {audit_results.get('threshold', 0):.4f}

## Feature Coverage
"""
    for feat, rate in quality_report["missingness"]["per_feature_missing_rate"].items():
        summary_md += f"- {feat}: {((1-rate)*100):.1f}% coverage\n"

    with open(os.path.join(REPORT_DIR, "preprocessing_summary.md"), "w") as f:
        f.write(summary_md)

    print(f"Preprocessing Complete. Master dataset saved to {processed_path}")
    if not audit_results["passed"]:
        exit(1)

if __name__ == "__main__":
    main()
