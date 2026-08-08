import os
import pandas as pd
import numpy as np
import json
import joblib
import hashlib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, recall_score, confusion_matrix

# --- CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROC_DATA = os.path.join(BASE_DIR, "datasets", "processed", "master_clinical_dataset.csv")
QUALITY_REPORT = os.path.join(BASE_DIR, "datasets", "metadata", "data_quality_report.json")
MODEL_DIR = os.path.join(BASE_DIR, "models", "clinical")
ASSET_DIR = os.path.join(BASE_DIR, "app_assets")

RANDOM_SEED = 42

def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def train():
    print("Initializing Clinical Training Pipeline...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(ASSET_DIR, exist_ok=True)

    # RF3: Leakage Check
    if not os.path.exists(QUALITY_REPORT):
        raise FileNotFoundError("Quality report missing. Run preprocess_clinical.py first.")

    with open(QUALITY_REPORT, "r") as f:
        quality = json.load(f)

    if not quality.get("leakage_audit_passed", False):
        raise ValueError("CRITICAL: Leakage audit failed in preprocessing. Aborting training.")

    # Load Data
    df = pd.read_csv(PROC_DATA)
    dataset_hash = compute_sha256(PROC_DATA)

    # Identify Features (Effective list from dataset)
    target_col = "category"
    excluded_cols = [target_col, "dataset_id"]
    feature_cols = [col for col in df.columns if col not in excluded_cols]

    print(f"Effective Feature List: {feature_cols}")

    # Split Data (Deterministic)
    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    # Build Unified Pipeline
    numeric_features = X.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_features = X.select_dtypes(include=['object']).columns.tolist()

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numeric_features),
            ('cat', Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('encoder', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
            ]), categorical_features)
        ]
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED))
    ])

    # Train
    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    weighted_f1 = f1_score(y_test, y_pred, average='weighted')

    # Per-class recall
    classes = pipeline.classes_
    recalls = recall_score(y_test, y_pred, average=None, labels=classes)
    class_recalls = dict(zip(classes, recalls))
    worst_recall = min(recalls)

    # Acceptance Criteria
    macro_f1_passed = macro_f1 >= 0.85
    worst_recall_passed = worst_recall >= 0.80

    # External Validation honesty (Proxy check)
    external_validation_status = "NOT_AVAILABLE"
    clinical_model_valid = False # Always false for Track B without true independent validation

    # Save Pipeline
    pipeline_path = os.path.join(MODEL_DIR, "clinical_model_pipeline.joblib")
    joblib.dump(pipeline, pipeline_path)

    # Manifest
    manifest = {
        "model_version": "1.0.0",
        "training_timestamp": str(datetime.now()),
        "seed": RANDOM_SEED,
        "effective_feature_list": feature_cols,
        "feature_order": feature_cols,
        "preprocessing": {
            "numeric": "median_impute + standard_scale",
            "categorical": "most_frequent_impute + ordinal_encode(unknown=-1)"
        },
        "dataset_hash": dataset_hash,
        "split_stats": {
            "train_size": len(X_train),
            "test_size": len(X_test),
            "label_distribution": y.value_counts().to_dict()
        },
        "metrics": {
            "accuracy": acc,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "worst_class_recall": worst_recall,
            "class_recalls": class_recalls
        },
        "acceptance_criteria": {
            "macro_f1_threshold": 0.85,
            "macro_f1_passed": bool(macro_f1_passed),
            "worst_recall_threshold": 0.80,
            "worst_recall_passed": bool(worst_recall_passed)
        },
        "clinical_model_valid": clinical_model_valid,
        "clinical_model_invalid_reason": "Missing independent clinical validation dataset.",
        "external_validation_status": external_validation_status
    }

    with open(os.path.join(MODEL_DIR, "model_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)

    # Export Assets for Android
    with open(os.path.join(ASSET_DIR, "model_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)
    with open(os.path.join(ASSET_DIR, "feature_columns.json"), "w") as f:
        json.dump(feature_cols, f, indent=4)
    with open(os.path.join(ASSET_DIR, "label_classes.json"), "w") as f:
        json.dump(classes.tolist(), f, indent=4)

    print(f"Training Complete. Pipeline saved to {pipeline_path}")
    print(f"Metrics: Accuracy={acc:.4f}, Macro F1={macro_f1:.4f}, Worst Recall={worst_recall:.4f}")

if __name__ == "__main__":
    train()
