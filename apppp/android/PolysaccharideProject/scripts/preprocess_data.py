"""
preprocess_data.py
==================
Part 2 — Clean every raw dataset, merge into master, export JSON for Android.
"""

import os
import json
import pandas as pd

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ALL   = os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_All")
PROC_DIR  = os.path.join(BASE_DIR, "datasets", "processed")
META_DIR  = os.path.join(BASE_DIR, "datasets", "metadata")
ASSET_DIR = os.path.join(BASE_DIR, "app_assets")


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply standard cleaning to a DataFrame."""
    df = df.drop_duplicates()
    df = df.dropna(how="all")

    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].fillna("Unknown").str.strip()

    return df.reset_index(drop=True)


def load_raw_file(filepath: str) -> pd.DataFrame:
    """Load a CSV or JSON file into a DataFrame."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return pd.read_csv(filepath)
    elif ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
    raise ValueError(f"Unsupported file type: {ext}")


def preprocess():
    print("=" * 60)
    print("POLYSACCHARIDE PROJECT — PART 2: PREPROCESSING")
    print(f"Reading from: {RAW_ALL}")
    print("=" * 60)

    for d in [PROC_DIR, ASSET_DIR, META_DIR]:
        os.makedirs(d, exist_ok=True)

    all_dfs = []
    raw_files = [f for f in os.listdir(RAW_ALL)
                 if f.endswith(".csv") or f.endswith(".json")]
    raw_files.sort()

    for filename in raw_files:
        filepath = os.path.join(RAW_ALL, filename)
        print(f"\n  Processing: {filename}")
        try:
            df = load_raw_file(filepath)
            print(f"    Raw shape: {df.shape}")
            df = clean_df(df)
            print(f"    Cleaned shape: {df.shape}")

            # Save cleaned copy (always as CSV)
            base = os.path.splitext(filename)[0]
            cleaned_name = f"cleaned_{base}.csv"
            df.to_csv(os.path.join(PROC_DIR, cleaned_name), index=False)
            print(f"    ✓ Saved → {cleaned_name}")
            all_dfs.append(df)
        except Exception as exc:
            print(f"    ✗ FAILED: {exc}")

    if not all_dfs:
        print("ERROR: No datasets could be loaded. Run download_datasets.py first.")
        return

    # ─── Master dataset ───────────────────────────────────────────────────────
    master_df = pd.concat(all_dfs, axis=0, ignore_index=True)
    # Re-clean after concat (fills any new NaNs from misaligned columns)
    master_df = clean_df(master_df)

    master_path = os.path.join(PROC_DIR, "master_combined_dataset.csv")
    master_df.to_csv(master_path, index=False)
    print(f"\n  ✓ Master dataset saved → {master_path}")
    print(f"    Shape: {master_df.shape}")

    # ─── Android JSON export ──────────────────────────────────────────────────
    json_path = os.path.join(ASSET_DIR, "master_dataset.json")
    master_df.to_json(json_path, orient="records", indent=2)
    print(f"  ✓ Android JSON saved → {json_path}")

    # ─── Data summary ─────────────────────────────────────────────────────────
    summary = {
        "total_rows": int(len(master_df)),
        "total_columns": int(len(master_df.columns)),
        "columns": master_df.columns.tolist(),
        "data_types": {k: str(v) for k, v in master_df.dtypes.to_dict().items()},
        "missing_values": {k: int(v) for k, v in master_df.isnull().sum().to_dict().items()},
        "unique_counts": {k: int(v) for k, v in master_df.nunique().to_dict().items()},
        "sample_records": master_df.head(5).to_dict(orient="records"),
    }
    summary_path = os.path.join(META_DIR, "data_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, default=str)
    print(f"  ✓ Data summary saved → {summary_path}")

    print("\n✅ Part 2 complete — preprocess_data.py finished.")


if __name__ == "__main__":
    preprocess()
