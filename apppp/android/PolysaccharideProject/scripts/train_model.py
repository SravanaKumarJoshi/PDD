"""
train_model.py
==============
Part 3 — Multi-model benchmark, best model selection, GridSearchCV tuning.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Suppress only sklearn convergence warnings (not all warnings)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", message=".*ConvergenceWarning.*")

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MASTER_DATA = os.path.join(BASE_DIR, "datasets", "processed", "master_combined_dataset.csv")
MODEL_DIR   = os.path.join(BASE_DIR, "models")

PREFERRED_TARGETS = ["category", "classification", "type", "carbohydrate_class"]


def detect_target(df: pd.DataFrame) -> str:
    """Auto-detect best target column."""
    for col in PREFERRED_TARGETS:
        if col in df.columns:
            unique_count = df[col].nunique()
            if 2 <= unique_count <= 20:
                print(f"  Target column auto-detected: '{col}' ({unique_count} unique classes)")
                return col
    # fallback: first string column with 2-20 unique values
    for col in df.select_dtypes(include=["object"]).columns:
        if 2 <= df[col].nunique() <= 20:
            print(f"  Fallback target: '{col}' ({df[col].nunique()} unique classes)")
            return col
    raise ValueError("No valid target column found. Ensure master dataset has a classification column.")


def train():
    print("=" * 60)
    print("POLYSACCHARIDE PROJECT — PART 3: MODEL TRAINING")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(MODEL_DIR, exist_ok=True)

    df = pd.read_csv(MASTER_DATA)
    print(f"  Master dataset loaded: {df.shape}")

    # ─── Target detection ─────────────────────────────────────────────────────
    target_col = detect_target(df)

    # Remove rows where target is NaN or 'Unknown'
    df = df[df[target_col].notna() & (df[target_col].astype(str) != "Unknown")]
    df = df.reset_index(drop=True)

    # Keep only classes with at least 3 samples (needed for stratified split)
    class_counts = df[target_col].value_counts()
    valid_classes = class_counts[class_counts >= 3].index
    df = df[df[target_col].isin(valid_classes)].reset_index(drop=True)
    print(f"  After filtering small classes: {df.shape}")

    # ─── Feature selection ────────────────────────────────────────────────────
    drop_cols = {"name", "scientific_name", "common_name", "pdb_like_id", "id",
                 "molecular_formula_repeat", "e_number", "food_application",
                 "medical_application", "biological_function", "description",
                 target_col}
    feature_cols = [c for c in df.columns if c not in drop_cols]
    print(f"  Feature columns ({len(feature_cols)}): {feature_cols}")

    # ─── Encode categoricals ──────────────────────────────────────────────────
    encoders = {}
    # In pandas 3.x, string columns may have dtype 'str' (not 'object').
    # To robustly handle all non-numeric columns, check pd.api.types.
    for col in feature_cols:
        if not pd.api.types.is_numeric_dtype(df[col]) or df[col].dtype == object:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].fillna("Unknown").astype(str))
            encoders[col] = le
        else:
            # Fill numeric NaN with median
            df[col] = df[col].fillna(df[col].median())

    target_le = LabelEncoder()
    df[target_col] = target_le.fit_transform(df[target_col].astype(str))
    encoders["target"] = target_le

    # Final safety: convert to numeric and fill any remaining NaN
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    X = df[feature_cols].values.astype(np.float32)
    y = df[target_col].values.astype(int)


    # ─── Scale ────────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ─── Train/test split ─────────────────────────────────────────────────────
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        print("  Warning: Stratified split failed, using random split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

    print(f"  Train: {X_train.shape}, Test: {X_test.shape}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # ─── 7-Model benchmark ────────────────────────────────────────────────────
    n_classes = len(np.unique(y))
    models = {
        "RandomForest":       RandomForestClassifier(n_estimators=100, random_state=42),
        "GradientBoosting":   GradientBoostingClassifier(n_estimators=100, random_state=42),
        "DecisionTree":       DecisionTreeClassifier(random_state=42),
        "KNN":                KNeighborsClassifier(n_neighbors=min(5, len(X_train) // n_classes)),
        "SVM":                SVC(probability=True, random_state=42),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "MLP":                MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
    }

    results = []
    best_acc = -1
    best_cv_mean = -1
    best_f1 = -1
    best_model = None
    best_model_name = ""

    print("\n  Benchmarking models...")
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc  = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        rec  = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
        f1   = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

        cv_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")
        cv_mean   = float(cv_scores.mean())
        cv_std    = float(cv_scores.std())

        entry = {
            "model": name, "accuracy": acc, "precision": prec,
            "recall": rec, "f1": f1,
            "cv_mean": cv_mean, "cv_std": cv_std,
        }
        results.append(entry)
        print(f"    {name:22s} acc={acc:.4f}  cv={cv_mean:.4f}±{cv_std:.4f}  f1={f1:.4f}")

        if acc > best_acc or (
            acc == best_acc and cv_mean > best_cv_mean
        ) or (
            acc == best_acc and cv_mean == best_cv_mean and f1 > best_f1
        ):
            best_acc        = acc
            best_cv_mean    = cv_mean
            best_f1         = f1
            best_model      = model
            best_model_name = name

    print(f"\n  Best model: {best_model_name} (acc={best_acc:.4f})")

    # ─── GridSearchCV tuning on RandomForest + GradientBoosting ──────────────
    print("\n  Running GridSearchCV tuning...")
    tuning_results = {}

    rf_params = {
        "n_estimators": [50, 100, 200],
        "max_depth":    [None, 5, 10],
        "min_samples_split": [2, 5],
    }
    gb_params = {
        "n_estimators":   [50, 100],
        "learning_rate":  [0.05, 0.1, 0.2],
        "max_depth":      [3, 5],
    }

    for (tname, tcls, tparams) in [
        ("RandomForest",     RandomForestClassifier(random_state=42),     rf_params),
        ("GradientBoosting", GradientBoostingClassifier(random_state=42), gb_params),
    ]:
        gs = GridSearchCV(tcls, tparams, cv=3, scoring="accuracy", n_jobs=-1)
        gs.fit(X_train, y_train)
        tuned_acc = float(accuracy_score(y_test, gs.best_estimator_.predict(X_test)))
        print(f"    {tname}: best_params={gs.best_params_}  tuned_acc={tuned_acc:.4f}")
        tuning_results[tname] = {
            "best_params": gs.best_params_,
            "tuned_accuracy": tuned_acc,
        }
        # Upgrade best model if tuned version is better
        if tuned_acc > best_acc:
            best_acc        = tuned_acc
            best_model      = gs.best_estimator_
            best_model_name = f"{tname}_Tuned"
            print(f"    ↑ New best: {best_model_name} ({best_acc:.4f})")

    # ─── Save artifacts ───────────────────────────────────────────────────────
    joblib.dump(best_model, os.path.join(MODEL_DIR, "trained_model.pkl"))
    joblib.dump(encoders,   os.path.join(MODEL_DIR, "label_encoders.pkl"))
    joblib.dump(scaler,     os.path.join(MODEL_DIR, "scaler.pkl"))

    with open(os.path.join(MODEL_DIR, "feature_columns.json"), "w") as f:
        json.dump(feature_cols, f, indent=2)

    metrics_payload = {
        "best_model": best_model_name,
        "best_accuracy": best_acc,
        "target_column": target_col,
        "target_classes": target_le.classes_.tolist(),
        "n_features": len(feature_cols),
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "results": results,
        "tuning_results": tuning_results,
        "generated_at": datetime.now().isoformat(),
    }
    with open(os.path.join(MODEL_DIR, "model_metrics.json"), "w") as f:
        json.dump(metrics_payload, f, indent=4)

    print(f"\n  ✓ Artifacts saved in: {MODEL_DIR}")
    print(f"    trained_model.pkl  ({best_model_name})")
    print(f"    label_encoders.pkl")
    print(f"    scaler.pkl")
    print(f"    feature_columns.json")
    print(f"    model_metrics.json")

    print("\n✅ Part 3 complete — train_model.py finished.")


if __name__ == "__main__":
    train()
