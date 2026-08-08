"""Automated versioned offline catalogue generator."""

import json
import hashlib
from datetime import datetime, timezone
import pandas as pd
from typing import Dict, Any, List
from shared.ml.config import APP_CONFIG

def generate_curated_catalogue(
    df_production: pd.DataFrame,
    target_count: int = 40,
    version: str = "1.0.0",
) -> Dict[str, Any]:
    """Select representative materials per category from production MySQL data and format versioned JSON."""
    if df_production.empty:
        raise ValueError("Production dataset is empty. Cannot generate catalogue.")

    categories = df_production["category"].unique()
    per_cat = max(1, target_count // len(categories)) if len(categories) > 0 else target_count

    selected_rows = []
    for cat in categories:
        cat_df = df_production[df_production["category"] == cat]
        # Sort by data completeness / biocompatibility if available
        if "biocompatibility" in cat_df.columns:
            cat_df = cat_df.sort_values(by="biocompatibility", ascending=False)
        selected_rows.append(cat_df.head(per_cat))

    selected_df = pd.concat(selected_rows, ignore_index=True) if selected_rows else df_production.head(target_count)
    selected_df = selected_df.head(target_count)

    materials_list = selected_df.to_dict(orient="records")

    for r in materials_list:
        for k, v in r.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                r[k] = str(v)
            elif pd.isna(v):
                r[k] = None

    # Compute dataset hash
    dataset_bytes = json.dumps(materials_list, sort_keys=True, default=str).encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()[:16]

    catalogue_payload = {
        "metadata": {
            "catalogue_version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_database": "filtered_polymers",
            "dataset_hash": dataset_hash,
            "total_items": len(materials_list),
            "generator_version": APP_CONFIG.get("offline_catalogue", {}).get("generator_version", "1.0.0"),
            "is_curated_offline": True,
        },
        "materials": materials_list,
    }

    return catalogue_payload
