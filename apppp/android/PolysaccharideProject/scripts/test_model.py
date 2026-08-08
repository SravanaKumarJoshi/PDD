"""
test_model.py
=============
Part 4 — Load trained model, run sanity checks, generate visualizations.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

warnings.filterwarnings("ignore")

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR   = os.path.join(BASE_DIR, "models")
REPORT_DIR  = os.path.join(BASE_DIR, "reports")
MASTER_DATA = os.path.join(BASE_DIR, "datasets", "processed", "master_combined_dataset.csv")

# 10 known polysaccharide sanity test cases
SANITY_CASES = [
    {"name": "Starch",             "source": "Plants",             "monomer_unit": "Glucose",
     "bond_type": "Alpha-1,4/1,6","molecular_weight_kda": 500,    "solubility": "Soluble",         "expected": "Storage"},
    {"name": "Cellulose",          "source": "Plants",             "monomer_unit": "Glucose",
     "bond_type": "Beta-1,4",     "molecular_weight_kda": 1000,   "solubility": "Insoluble",       "expected": "Structural"},
    {"name": "Glycogen",           "source": "Animals",            "monomer_unit": "Glucose",
     "bond_type": "Alpha-1,4/1,6","molecular_weight_kda": 800,    "solubility": "Soluble",         "expected": "Storage"},
    {"name": "Xanthan Gum",        "source": "Bacteria",           "monomer_unit": "Glucose/Mannose/GlcA",
     "bond_type": "Mixed",        "molecular_weight_kda": 3000,   "solubility": "Soluble",         "expected": "Bacterial"},
    {"name": "Heparin",            "source": "Animals",            "monomer_unit": "Glucosamine/Uronic",
     "bond_type": "Alpha-1,4",    "molecular_weight_kda": 15,     "solubility": "Soluble",         "expected": "Bioactive"},
    {"name": "Agar",               "source": "Red Algae",          "monomer_unit": "Galactose",
     "bond_type": "Mixed",        "molecular_weight_kda": 150,    "solubility": "Soluble (Hot)",   "expected": "Algal"},
    {"name": "Pullulan",           "source": "Fungi",              "monomer_unit": "Glucose",
     "bond_type": "Alpha-1,4/1,6","molecular_weight_kda": 300,    "solubility": "Soluble",         "expected": "Fungal"},
    {"name": "Hyaluronic Acid",    "source": "Animals/Bacteria",   "monomer_unit": "Glucuronic/Glucosamine",
     "bond_type": "Beta-1,3",     "molecular_weight_kda": 2000,   "solubility": "Soluble",         "expected": "Bioactive"},
    {"name": "Inulin",             "source": "Plants",             "monomer_unit": "Fructose",
     "bond_type": "Beta-2,1",     "molecular_weight_kda": 5,      "solubility": "Soluble",         "expected": "Storage"},
    {"name": "Chitin",             "source": "Fungi/Exoskeletons", "monomer_unit": "N-acetylglucosamine",
     "bond_type": "Beta-1,4",     "molecular_weight_kda": 700,    "solubility": "Insoluble",       "expected": "Structural"},
]


def safe_encode(encoder, value: str):
    """Encode a value, falling back to the closest match if unseen."""
    classes = list(encoder.classes_)
    if value in classes:
        return encoder.transform([value])[0]
    # partial match fallback
    for c in classes:
        if value.lower() in c.lower() or c.lower() in value.lower():
            return encoder.transform([c])[0]
    # last resort: 0
    return 0


def test():
    print("=" * 60)
    print("POLYSACCHARIDE PROJECT — PART 4: MODEL TESTING")
    print("=" * 60)

    os.makedirs(REPORT_DIR, exist_ok=True)

    # ─── Load artifacts ───────────────────────────────────────────────────────
    model    = joblib.load(os.path.join(MODEL_DIR, "trained_model.pkl"))
    encoders = joblib.load(os.path.join(MODEL_DIR, "label_encoders.pkl"))
    scaler   = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))

    with open(os.path.join(MODEL_DIR, "feature_columns.json"), "r") as f:
        feature_cols = json.load(f)

    with open(os.path.join(MODEL_DIR, "model_metrics.json"), "r") as f:
        metrics = json.load(f)

    target_le = encoders["target"]
    print(f"  Model: {metrics['best_model']}")
    print(f"  Classes: {target_le.classes_.tolist()}")
    print(f"  Features: {feature_cols}")

    # ─── Full dataset predictions for confusion matrix ─────────────────────────
    df = pd.read_csv(MASTER_DATA)
    target_col = metrics.get("target_column", "category")
    df = df[df[target_col].notna() & (df[target_col].astype(str) != "Unknown")]

    # Keep rows where target is in known classes
    known_targets = set(target_le.classes_)
    df = df[df[target_col].isin(known_targets)].copy()

    for col in feature_cols:
        if col in encoders and col != "target":
            df[col] = df[col].apply(
                lambda v: safe_encode(encoders[col], str(v))
            )

    X_all    = df[feature_cols].values.astype(float)
    y_true   = target_le.transform(df[target_col].astype(str))
    X_scaled = scaler.transform(X_all)
    y_pred   = model.predict(X_scaled)

    # ─── Confusion Matrix ─────────────────────────────────────────────────────
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=target_le.classes_,
                yticklabels=target_le.classes_, ax=ax)
    ax.set_title("Confusion Matrix — Polysaccharide Classification", fontsize=14, fontweight="bold")
    ax.set_ylabel("True Label", fontsize=12)
    ax.set_xlabel("Predicted Label", fontsize=12)
    plt.tight_layout()
    cm_path = os.path.join(REPORT_DIR, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=150)
    plt.close()
    print(f"\n  ✓ confusion_matrix.png saved")

    # ─── Model comparison bar chart ───────────────────────────────────────────
    model_names = [r["model"] for r in metrics["results"]]
    accuracies  = [r["accuracy"] for r in metrics["results"]]
    f1_scores   = [r["f1"] for r in metrics["results"]]
    cv_means    = [r["cv_mean"] for r in metrics["results"]]

    x = np.arange(len(model_names))
    w = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    bars1 = ax.bar(x - w, accuracies, w, label="Test Accuracy", color="#4C72B0")
    bars2 = ax.bar(x,     f1_scores,  w, label="F1 (weighted)", color="#DD8452")
    bars3 = ax.bar(x + w, cv_means,   w, label="CV Mean",       color="#55A868")

    ax.set_xlabel("Model")
    ax.set_ylabel("Score")
    ax.set_title("Model Comparison — Polysaccharide Classification", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=25, ha="right")
    ax.set_ylim(0, 1.15)
    ax.legend()
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)

    for bar in list(bars1) + list(bars2) + list(bars3):
        height = bar.get_height()
        ax.annotate(f"{height:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7)

    plt.tight_layout()
    comp_path = os.path.join(REPORT_DIR, "model_comparison.png")
    plt.savefig(comp_path, dpi=150)
    plt.close()
    print(f"  ✓ model_comparison.png saved")

    # ─── Sanity checks ────────────────────────────────────────────────────────
    print("\n  Running 10-case sanity checks...")
    sanity_results = []
    for case in SANITY_CASES:
        row = []
        for col in feature_cols:
            if col not in case:
                row.append(0)
            elif col in encoders and col != "target":
                row.append(safe_encode(encoders[col], str(case[col])))
            else:
                try:
                    row.append(float(case[col]))
                except (ValueError, TypeError):
                    row.append(0)

        x_in = scaler.transform([row])
        pred_idx    = model.predict(x_in)[0]
        prediction  = target_le.inverse_transform([pred_idx])[0]

        # Confidence via predict_proba if available
        confidence = None
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x_in)[0]
            confidence = round(float(proba.max()), 4)

        match = case["expected"].lower() == prediction.lower()
        result_entry = {
            "polysaccharide": case["name"],
            "expected":       case["expected"],
            "predicted":      prediction,
            "confidence":     confidence,
            "match":          match,
        }
        sanity_results.append(result_entry)
        icon = "✓" if match else "✗"
        print(f"    {icon} {case['name']:22s}  expected={case['expected']:12s}  predicted={prediction:12s}  conf={confidence}")

    matches = sum(1 for r in sanity_results if r["match"])
    print(f"\n  Sanity accuracy: {matches}/{len(sanity_results)}")

    # ─── Save test_results.json ───────────────────────────────────────────────
    test_results = {
        "model": metrics["best_model"],
        "sanity_accuracy": matches / len(sanity_results),
        "sanity_results": sanity_results,
        "confusion_matrix_saved": cm_path,
        "model_comparison_saved": comp_path,
    }
    results_path = os.path.join(REPORT_DIR, "test_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=4)
    print(f"\n  ✓ test_results.json saved → {results_path}")
    print("\n✅ Part 4 complete — test_model.py finished.")


if __name__ == "__main__":
    test()
