"""Configuration loader for the shared ML library."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"

def load_yaml_config(filename: str) -> Dict[str, Any]:
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

TRAINING_CONFIG = load_yaml_config("training_config.yaml")
SCREENING_CONFIG = load_yaml_config("screening_config.yaml")
APP_CONFIG = load_yaml_config("app_config.yaml")

# Fallback defaults if config files are missing
FEATURE_COLUMNS: List[str] = TRAINING_CONFIG.get("feature_columns", [
    "tensile_strength",
    "elastic_modulus",
    "elongation_pct",
    "flexibility",
    "wvtr",
    "oxygen_permeability",
    "biocompatibility",
    "toxicity_score",
    "antimicrobial",
    "biodegradation_days",
    "environmental_impact",
    "film_forming",
    "sterilization_gamma",
    "sterilization_eto",
    "sterilization_steam",
])

MATERIAL_TABLE_NAME: str = os.getenv(
    "MATERIAL_TABLE_NAME",
    APP_CONFIG.get("database", {}).get("table_name", "filtered_polymers")
)
