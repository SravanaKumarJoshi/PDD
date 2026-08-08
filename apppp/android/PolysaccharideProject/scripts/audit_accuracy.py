import os
import pandas as pd
import json
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

# --- CONFIGURATION ---
BASE_DIR = "D:/Sravan/PDD/apppp/android/PolysaccharideProject"
PROC_DATA = os.path.join(BASE_DIR, "datasets", "processed", "master_clinical_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models", "clinical")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

RANDOM_SEED = 42

def audit():
    print("Running Independent Accuracy Audit...")
    
    # Load Artifacts
    pipeline_path = os.path.join(MODEL_DIR, "clinical_model_pipeline.joblib")
    manifest_path = os.path.join(MODEL_DIR, "model_manifest.json")
    test_results_path = os.path.join(REPORT_DIR, "clinical_test_results.json")
    
    pipeline = joblib.load(pipeline_path)
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    with open(test_results_path, "r") as f:
        test_results = json.load(f)

    # Load Data
    df = pd.read_csv(PROC_DATA)
    feature_cols = manifest["effective_feature_list"]
    target_col = "category"

    # Reproduce Test Split exactly
    X = df[feature_cols]
    y = df[target_col]
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    # Recompute Metrics
    y_pred = pipeline.predict(X_test)
    recomputed_acc = accuracy_score(y_test, y_pred)
    recomputed_f1 = f1_score(y_test, y_pred, average='macro')

    # Verification Gate
    mismatch_found = False
    tolerance = 1e-6
    
    if abs(recomputed_acc - manifest["metrics"]["accuracy"]) > tolerance:
        print(f"FAIL: Accuracy mismatch! Manifest: {manifest['metrics']['accuracy']}, Audit: {recomputed_acc}")
        mismatch_found = True
    
    if abs(recomputed_acc - test_results["accuracy"]) > tolerance:
        print(f"FAIL: Accuracy mismatch! Test Results: {test_results['accuracy']}, Audit: {recomputed_acc}")
        mismatch_found = True

    audit_data = {
        "recomputed_accuracy": recomputed_acc,
        "recomputed_macro_f1": recomputed_f1,
        "audit_timestamp": str(pd.Timestamp.now()),
        "audit_passed": not mismatch_found
    }

    with open(os.path.join(REPORT_DIR, "model_accuracy_recompute.json"), "w") as f:
        json.dump(audit_data, f, indent=4)

    if mismatch_found:
        print("Audit FAILED.")
        exit(1)
    else:
        print("Audit PASSED. Metrics match exactly.")

if __name__ == "__main__":
    audit()
