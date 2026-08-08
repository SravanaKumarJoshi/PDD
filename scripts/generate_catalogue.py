#!/usr/bin/env python3
"""
generate_catalogue.py — Standalone Offline Catalogue Generator

Queries MySQL dataset, applies selection rules per category, and writes
versioned JSON output for Android asset bundling.
"""

import os
import sys
import json
import argparse
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.ml.config import APP_CONFIG, MATERIAL_TABLE_NAME
from shared.ml.catalogue_generator import generate_curated_catalogue

def main():
    parser = argparse.ArgumentParser(description="Generate Curated Offline Catalogue")
    parser.add_argument("--count", type=int, default=40, help="Number of curated materials to include")
    args = parser.parse_args()

    print("[CatalogueGenerator] Querying production dataset...")

    # Load from MySQL or synthetic fallback
    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:root123@localhost:3306/polysaccharide_selector")
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        df = pd.read_sql(f"SELECT * FROM {MATERIAL_TABLE_NAME}", engine)
    except Exception as e:
        print(f"[CatalogueGenerator] Warning: MySQL connection error ({e}). Generating fallback catalogue data.")
        # Fallback representative dataset
        df = pd.DataFrame([
            {"polymer": "Chitosan", "category": "Polysaccharide", "tensile_strength": 45.0, "elastic_modulus": 2.5, "wvtr": 250.0, "biocompatibility": 9.0, "toxicity_score": 9.5, "biodegradation_days": 60, "sterilization_gamma": 1, "sterilization_eto": 1, "sterilization_steam": 0},
            {"polymer": "Alginate", "category": "Polysaccharide", "tensile_strength": 35.0, "elastic_modulus": 1.8, "wvtr": 320.0, "biocompatibility": 8.5, "toxicity_score": 9.0, "biodegradation_days": 45, "sterilization_gamma": 1, "sterilization_eto": 1, "sterilization_steam": 0},
            {"polymer": "Hyaluronic Acid", "category": "Polysaccharide", "tensile_strength": 15.0, "elastic_modulus": 0.5, "wvtr": 450.0, "biocompatibility": 9.8, "toxicity_score": 10.0, "biodegradation_days": 14, "sterilization_gamma": 0, "sterilization_eto": 1, "sterilization_steam": 0},
            {"polymer": "Cellulose Acetate", "category": "Polysaccharide Derivative", "tensile_strength": 65.0, "elastic_modulus": 3.2, "wvtr": 180.0, "biocompatibility": 7.5, "toxicity_score": 8.0, "biodegradation_days": 180, "sterilization_gamma": 1, "sterilization_eto": 1, "sterilization_steam": 1},
            {"polymer": "PLLA", "category": "Synthetic Biopolymer", "tensile_strength": 70.0, "elastic_modulus": 3.5, "wvtr": 120.0, "biocompatibility": 8.0, "toxicity_score": 8.5, "biodegradation_days": 365, "sterilization_gamma": 1, "sterilization_eto": 1, "sterilization_steam": 0},
            {"polymer": "PCL", "category": "Synthetic Biopolymer", "tensile_strength": 25.0, "elastic_modulus": 0.4, "wvtr": 150.0, "biocompatibility": 8.2, "toxicity_score": 8.5, "biodegradation_days": 730, "sterilization_gamma": 1, "sterilization_eto": 1, "sterilization_steam": 0},
        ])

    catalogue_json = generate_curated_catalogue(df, target_count=args.count)

    out_rel = APP_CONFIG.get("offline_catalogue", {}).get(
        "output_path", "apppp/android/app/src/main/assets/curated_catalogue.json"
    )
    out_path = ROOT_DIR / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalogue_json, f, indent=2)

    print(f"[CatalogueGenerator] Curated catalogue generated successfully -> {out_path}")
    print(f"[CatalogueGenerator] Items: {catalogue_json['metadata']['total_items']}, Hash: {catalogue_json['metadata']['dataset_hash']}")

if __name__ == "__main__":
    main()
