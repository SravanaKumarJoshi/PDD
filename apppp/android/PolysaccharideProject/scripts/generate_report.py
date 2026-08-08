"""
generate_report.py
==================
Part 6 — Generate professional Markdown reports from all pipeline outputs.
"""

import os
import json
from datetime import datetime
import pandas as pd

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORT_DIR = os.path.join(BASE_DIR, "reports")
META_DIR   = os.path.join(BASE_DIR, "datasets", "metadata")
MODEL_DIR  = os.path.join(BASE_DIR, "models")
RAW_ALL    = os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_All")

SINGLE_FOLDER_NAME = "Polysaccharide_Datasets_All"
SINGLE_FOLDER_PATH = RAW_ALL


def load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  WARNING: Could not load {path}: {exc}")
        return {}


def generate_report():
    print("=" * 60)
    print("POLYSACCHARIDE PROJECT — PART 6: REPORT GENERATION")
    print("=" * 60)

    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    catalog  = load_json(os.path.join(META_DIR, "dataset_catalog.json"))
    summary  = load_json(os.path.join(META_DIR, "data_summary.json"))
    metrics  = load_json(os.path.join(MODEL_DIR, "model_metrics.json"))
    test_res = load_json(os.path.join(REPORT_DIR, "test_results.json"))

    # ── 1. full_report.md ────────────────────────────────────────────────────
    catalog_rows = ""
    if isinstance(catalog, list):
        for e in catalog:
            catalog_rows += (
                f"| {e.get('id','?')} | {e.get('name','?')} | "
                f"{e.get('source_name','?')} | [{e.get('source_url','N/A')}]({e.get('source_url','#')}) | "
                f"{e.get('row_count','?')} rows | {e.get('download_status','?')} |\n"
            )

    model_rows = ""
    tuning_section = ""
    if isinstance(metrics, dict):
        for r in metrics.get("results", []):
            model_rows += (
                f"| {r['model']} | {r['accuracy']:.4f} | {r['precision']:.4f} | "
                f"{r['recall']:.4f} | {r['f1']:.4f} | "
                f"{r['cv_mean']:.4f}±{r['cv_std']:.4f} |\n"
            )
        for tname, tres in metrics.get("tuning_results", {}).items():
            tuning_section += (
                f"**{tname}**: Best params = `{tres['best_params']}`, "
                f"Tuned accuracy = `{tres['tuned_accuracy']:.4f}`\n\n"
            )

    sanity_rows = ""
    if isinstance(test_res, dict):
        for r in test_res.get("sanity_results", []):
            icon = "✅" if r["match"] else "❌"
            sanity_rows += (
                f"| {r['polysaccharide']} | {r['expected']} | {r['predicted']} | "
                f"{r.get('confidence','N/A')} | {icon} |\n"
            )

    full_report = f"""# 🔬 Polysaccharide ML Project — Full Report

**Generated:** {now}  
**Project Root:** `{BASE_DIR}`  
**Raw Dataset Folder:** `Polysaccharide_Datasets_All`  
**Raw Dataset Path:** `{SINGLE_FOLDER_PATH}`

---

## 1. Project Overview

This end-to-end pipeline classifies polysaccharides based on their chemical and physical
properties using a multi-model machine learning approach. It covers dataset acquisition,
preprocessing, 7-model benchmarking, GridSearchCV tuning, TFLite conversion, and Android
integration.

---

## 2. Dataset Storage — Single-Folder Rule

> **All downloaded datasets are stored in ONE folder named:**
> **`{SINGLE_FOLDER_NAME}`**
> **at:** `{SINGLE_FOLDER_PATH}`

Total datasets: {len(catalog) if isinstance(catalog, list) else 'N/A'}  
Master dataset rows: {summary.get('total_rows', 'N/A')}  
Master dataset columns: {summary.get('total_columns', 'N/A')}

### Dataset Catalog

| ID | Name | Source | URL | Rows | Status |
|----|------|--------|-----|------|--------|
{catalog_rows}
---

## 3. Preprocessing Steps

1. All raw CSV and JSON files read from `Polysaccharide_Datasets_All/`
2. Duplicates dropped
3. Fully-empty rows removed
4. Numeric missing values filled with **column median**
5. String missing values filled with `"Unknown"`, whitespace stripped
6. Cleaned files saved as `cleaned_<filename>.csv` in `datasets/processed/`
7. All cleaned frames concatenated → `master_combined_dataset.csv`
8. Master dataset exported to `app_assets/master_dataset.json` (Android format)

---

## 4. Model Training Results

| Model | Accuracy | Precision | Recall | F1 | CV (5-fold) |
|-------|----------|-----------|--------|----|-------------|
{model_rows}

**Best Model Selected:** `{metrics.get('best_model', 'N/A')}`  
**Best Test Accuracy:** `{metrics.get('best_accuracy', 'N/A')}`  
**Target Column:** `{metrics.get('target_column', 'N/A')}`  
**Classes:** {metrics.get('target_classes', [])}

### GridSearchCV Tuning

{tuning_section if tuning_section else "No tuning results found."}

---

## 5. Model Testing

**Sanity accuracy:** {test_res.get('sanity_accuracy', 'N/A')}

| Polysaccharide | Expected | Predicted | Confidence | Match |
|----------------|----------|-----------|------------|-------|
{sanity_rows}

---

## 6. TFLite Conversion for Android

The Keras proxy model (layers: 128 → 64 → 32 → softmax) was compiled and converted
to an optimized TFLite model for Android deployment.

- `models/trained_model.tflite`
- `app_assets/trained_model.tflite`
- `app_assets/feature_columns.json`
- `app_assets/label_classes.json`
- `app_assets/scaler_params.json`

---

## 7. File Inventory

| Category | File | Path |
|----------|------|------|
| Raw datasets | All 10 files | `{SINGLE_FOLDER_PATH}` |
| Best model | trained_model.pkl | `{MODEL_DIR}` |
| TFLite | trained_model.tflite | `{MODEL_DIR}` |
| Android assets | master_dataset.json | `{BASE_DIR}\\app_assets` |
| Reports | full_report.md | `{REPORT_DIR}` |

---

## 8. Android Integration

Add to `app/build.gradle.kts`:
```kotlin
implementation("org.tensorflow:tensorflow-lite:2.14.0")
implementation("org.tensorflow:tensorflow-lite-support:0.4.4")
```
Copy `app_assets/` → `app/src/main/assets/`

---

*Report generated automatically by `generate_report.py`*
"""

    with open(os.path.join(REPORT_DIR, "full_report.md"), "w", encoding="utf-8") as f:
        f.write(full_report)
    print("  ✓ full_report.md saved")

    # ── 2. training_results.md ───────────────────────────────────────────────
    training_md = f"""# Training Results

Generated: {now}

## Best Model: {metrics.get('best_model', 'N/A')}

| Model | Accuracy | Precision | Recall | F1 | CV Mean | CV Std |
|-------|----------|-----------|--------|----|---------|--------|
{model_rows}

## GridSearchCV Tuning

{tuning_section if tuning_section else "Not available."}

## Configuration
- Train/Test split: 80% / 20% (stratified)
- CV: 5-fold StratifiedKFold
- Feature columns: {metrics.get('n_features', 'N/A')}
- Train samples: {metrics.get('train_samples', 'N/A')}
- Test samples: {metrics.get('test_samples', 'N/A')}
"""
    with open(os.path.join(REPORT_DIR, "training_results.md"), "w", encoding="utf-8") as f:
        f.write(training_md)
    print("  ✓ training_results.md saved")

    # ── 3. dataset_summary.md ────────────────────────────────────────────────
    col_types = "\n".join(
        [f"| {col} | {dtype} |" for col, dtype in summary.get("data_types", {}).items()]
    )
    dataset_md = f"""# Dataset Summary

Generated: {now}

## Single Folder Rule
All raw datasets stored in ONE folder:
- **Folder name:** `{SINGLE_FOLDER_NAME}`
- **Path:** `{SINGLE_FOLDER_PATH}`

## Master Dataset Stats
- **Total rows:** {summary.get('total_rows', 'N/A')}
- **Total columns:** {summary.get('total_columns', 'N/A')}
- **Columns:** {summary.get('columns', [])}

## Column Data Types

| Column | Type |
|--------|------|
{col_types}

## Catalog
| ID | Name | Rows | Format | Status |
|----|------|------|--------|--------|
"""
    if isinstance(catalog, list):
        for e in catalog:
            dataset_md += f"| {e.get('id')} | {e.get('name')} | {e.get('row_count')} | {e.get('format')} | {e.get('download_status')} |\n"

    with open(os.path.join(REPORT_DIR, "dataset_summary.md"), "w", encoding="utf-8") as f:
        f.write(dataset_md)
    print("  ✓ dataset_summary.md saved")

    # ── 4. dataset_paths.txt ─────────────────────────────────────────────────
    paths_content = generate_paths_txt(BASE_DIR, SINGLE_FOLDER_NAME, RAW_ALL, catalog)
    paths_file = os.path.join(BASE_DIR, "dataset_paths.txt")
    with open(paths_file, "w", encoding="utf-8") as f:
        f.write(paths_content)
    print(f"  ✓ dataset_paths.txt saved → {paths_file}")

    print("\n✅ Part 6 complete — generate_report.py finished.")


def generate_paths_txt(base: str, folder_name: str, raw_path: str, catalog) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("POLYSACCHARIDE PROJECT — ABSOLUTE FILE PATH REFERENCE")
    lines.append("=" * 70)
    lines.append("")
    lines.append("All downloaded datasets are stored in ONE folder named:")
    lines.append(f"  {folder_name}")
    lines.append(f"  at: {raw_path}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("RAW DATASETS (Polysaccharide_Datasets_All)")
    lines.append("─" * 70)
    if isinstance(catalog, list):
        for e in catalog:
            lines.append(f"  {e.get('filename','?'):50s}  {e.get('local_path','?')}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("PROCESSED DATASETS")
    lines.append("─" * 70)
    proc = os.path.join(base, "datasets", "processed")
    if os.path.isdir(proc):
        for f in sorted(os.listdir(proc)):
            lines.append(f"  {f:50s}  {os.path.join(proc, f)}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("MODEL ARTIFACTS")
    lines.append("─" * 70)
    model_dir = os.path.join(base, "models")
    for fname in ["trained_model.pkl", "trained_model.tflite", "label_encoders.pkl",
                  "scaler.pkl", "feature_columns.json", "model_metrics.json"]:
        lines.append(f"  {fname:50s}  {os.path.join(model_dir, fname)}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("REPORTS")
    lines.append("─" * 70)
    rep_dir = os.path.join(base, "reports")
    for fname in ["full_report.md", "training_results.md", "dataset_summary.md",
                  "confusion_matrix.png", "model_comparison.png", "test_results.json"]:
        lines.append(f"  {fname:50s}  {os.path.join(rep_dir, fname)}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("APP ASSETS (copy to Android app/src/main/assets/)")
    lines.append("─" * 70)
    asset_dir = os.path.join(base, "app_assets")
    android_assets = os.path.join(
        os.path.dirname(base), "app", "src", "main", "assets"
    )
    for fname in ["master_dataset.json", "trained_model.tflite",
                  "feature_columns.json", "label_classes.json", "scaler_params.json"]:
        src = os.path.join(asset_dir, fname)
        dst = os.path.join(android_assets, fname)
        lines.append(f"  {fname:50s}  src: {src}")
        lines.append(f"  {'':50s}  dst: {dst}")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


if __name__ == "__main__":
    generate_report()
