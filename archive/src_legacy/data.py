"""
Data loading, validation, and MySQL connectivity module.

All material data is loaded from MySQL exclusively.
MongoDB references have been removed.
"""
from __future__ import annotations

import os
import time
import contextlib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env from the project root (one level above this file's directory)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Module-level dataset cache — avoids re-querying MySQL on every Streamlit
# rerun. Cache expires after CACHE_TTL_SECONDS (default 5 minutes).
# ---------------------------------------------------------------------------
_dataset_cache: dict = {
    "df": None,
    "stats": None,
    "loaded_at": 0.0,
}
_CACHE_TTL_SECONDS: float = 300.0


# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "polymer", "category", "tensile_strength", "elastic_modulus",
    "elongation_pct", "flexibility", "wvtr", "oxygen_permeability",
    "biocompatibility", "toxicity_score", "antimicrobial",
    "biodegradation_days", "environmental_impact", "solubility",
    "film_forming", "sterilization_gamma", "sterilization_eto",
    "sterilization_steam", "cost_band", "availability_band",
    "evidence_level", "source_doi", "is_augmented",
    "suitability_label", "data_completeness",
]

NUMERIC_COLUMNS = [
    "tensile_strength", "elastic_modulus", "elongation_pct",
    "flexibility", "wvtr", "oxygen_permeability",
    "biocompatibility", "toxicity_score", "antimicrobial",
    "biodegradation_days", "environmental_impact",
    "film_forming", "sterilization_gamma", "sterilization_eto",
    "sterilization_steam", "is_augmented", "suitability_label",
    "data_completeness",
]

FEATURE_COLUMNS = [
    "tensile_strength", "elastic_modulus", "elongation_pct",
    "flexibility", "wvtr", "oxygen_permeability",
    "biocompatibility", "toxicity_score", "antimicrobial",
    "biodegradation_days", "environmental_impact",
    "film_forming", "sterilization_gamma", "sterilization_eto",
    "sterilization_steam",
]


def standardize_material_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame columns conform to the standard schema used across ML pipeline and UI."""
    if df is None or df.empty:
        return df

    df = df.copy()

    column_mapping = {
        "name": "polymer",
        "tensileStrengthMpaMin": "tensile_strength",
        "tensileStrengthMpaMax": "tensile_strength_max",
        "elasticModulusGpaMin": "elastic_modulus",
        "elasticModulusGpaMax": "elastic_modulus_max",
        "elongationPctMin": "elongation_pct",
        "degradationDaysMin": "biodegradation_days",
        "enzymaticDegradability": "environmental_impact",
        "cytotoxicitySafe": "cytotoxicity_safe",
        "sterGamma": "sterilization_gamma",
        "sterEto": "sterilization_eto",
        "sterSteam": "sterilization_steam",
        "procFilm": "film_forming",
        "evidenceLevel": "evidence_level",
    }

    rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns and new not in df.columns}
    if rename_dict:
        df = df.rename(columns=rename_dict)

    if "polymer" not in df.columns:
        if "name" in df.columns:
            df["polymer"] = df["name"]
        else:
            df["polymer"] = "Unknown Polymer"

    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    if "biocompatibility" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["biocompatibility"] = df["cytotoxicity_safe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        elif "cytotoxicitySafe" in df.columns:
            df["biocompatibility"] = df["cytotoxicitySafe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        else:
            df["biocompatibility"] = 8.0

    if "toxicity_score" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["toxicity_score"] = df["cytotoxicity_safe"].apply(
                lambda x: 8.5 if str(x).strip() in ["1", "1.0", "True", "true"] else 3.0
            )
        else:
            df["toxicity_score"] = 8.0

    if "tensile_strength" not in df.columns:
        if "tensileStrengthMpaMin" in df.columns:
            df["tensile_strength"] = pd.to_numeric(df["tensileStrengthMpaMin"], errors="coerce").fillna(20.0)
        else:
            df["tensile_strength"] = 20.0

    if "elastic_modulus" not in df.columns:
        if "elasticModulusGpaMin" in df.columns:
            df["elastic_modulus"] = pd.to_numeric(df["elasticModulusGpaMin"], errors="coerce").fillna(1.2)
        else:
            df["elastic_modulus"] = 1.2

    if "elongation_pct" not in df.columns:
        if "elongationPctMin" in df.columns:
            df["elongation_pct"] = pd.to_numeric(df["elongationPctMin"], errors="coerce").fillna(45.0)
        else:
            df["elongation_pct"] = 45.0

    if "flexibility" not in df.columns:
        if "elongation_pct" in df.columns:
            df["flexibility"] = pd.to_numeric(df["elongation_pct"], errors="coerce").fillna(45.0) * 0.8
        else:
            df["flexibility"] = 35.0

    if "wvtr" not in df.columns:
        df["wvtr"] = 800.0

    if "oxygen_permeability" not in df.columns:
        if "otr" in df.columns:
            df["oxygen_permeability"] = pd.to_numeric(df["otr"], errors="coerce").fillna(120.0)
        else:
            df["oxygen_permeability"] = 120.0

    if "antimicrobial" not in df.columns:
        df["antimicrobial"] = 0.0

    if "biodegradation_days" not in df.columns:
        if "degradationDaysMin" in df.columns:
            df["biodegradation_days"] = pd.to_numeric(df["degradationDaysMin"], errors="coerce").fillna(60.0)
        else:
            df["biodegradation_days"] = 60.0

    if "environmental_impact" not in df.columns:
        df["environmental_impact"] = 5.0

    if "film_forming" not in df.columns:
        df["film_forming"] = 1.0

    if "sterilization_gamma" not in df.columns:
        df["sterilization_gamma"] = 0.0

    if "sterilization_eto" not in df.columns:
        df["sterilization_eto"] = 0.0

    if "sterilization_steam" not in df.columns:
        df["sterilization_steam"] = 0.0

    if "is_augmented" not in df.columns:
        df["is_augmented"] = 0

    if "evidence_level" not in df.columns:
        df["evidence_level"] = "high"

    if "suitability_label" not in df.columns:
        if "biocompatibility" in df.columns:
            bio = pd.to_numeric(df["biocompatibility"], errors="coerce").fillna(5.0)
            df["suitability_label"] = (bio >= bio.median()).astype(int)
        else:
            df["suitability_label"] = 1

    return df


# ---------------------------------------------------------------------------
# MySQL connection
# ---------------------------------------------------------------------------

def _get_mysql_config() -> dict:
    """Read MySQL credentials from environment variables.

    Priority: individual MYSQL_* vars (from .env) → DATABASE_URL fallback.
    Never hardcode credentials here.
    """
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    database = os.environ.get("MYSQL_DATABASE", "polysaccharide_selector")
    user = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "root123")
    # connection_timeout: seconds to wait for the TCP handshake
    # read_timeout / write_timeout: seconds to wait for a query response
    connection_timeout = int(os.environ.get("MYSQL_CONNECTION_TIMEOUT", "10"))
    read_timeout = int(os.environ.get("MYSQL_READ_TIMEOUT", "30"))
    return dict(
        host=host, port=port, database=database,
        user=user, password=password,
        connection_timeout=connection_timeout,
        read_timeout=read_timeout,
        write_timeout=read_timeout,
    )


@contextlib.contextmanager
def mysql_connection():
    """Context manager that yields an open mysql-connector-python connection.

    Usage::

        with mysql_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM filtered_polymers")
            rows = cursor.fetchall()
            cursor.close()

    The connection is committed and closed automatically.
    Raises RuntimeError with a helpful message if mysql-connector-python is
    not installed or the credentials are wrong.
    """
    try:
        import mysql.connector
    except ImportError:
        raise RuntimeError(
            "mysql-connector-python is not installed. "
            "Run: pip install mysql-connector-python"
        )

    cfg = _get_mysql_config()
    conn = None
    try:
        conn = mysql.connector.connect(**cfg)
        yield conn
        conn.commit()
    except mysql.connector.Error as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        raise RuntimeError(
            f"MySQL connection failed ({cfg['host']}:{cfg['port']} "
            f"db={cfg['database']} user={cfg['user']}): {exc}"
        ) from exc
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


# ---------------------------------------------------------------------------
# Dataset loading — MySQL primary, CSV fallback
# ---------------------------------------------------------------------------

def standardize_material_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame columns conform to the standard schema used across ML pipeline and UI."""
    if df is None or df.empty:
        return df

    df = df.copy()

    column_mapping = {
        "name": "polymer",
        "tensileStrengthMpaMin": "tensile_strength",
        "tensileStrengthMpaMax": "tensile_strength_max",
        "elasticModulusGpaMin": "elastic_modulus",
        "elasticModulusGpaMax": "elastic_modulus_max",
        "elongationPctMin": "elongation_pct",
        "degradationDaysMin": "biodegradation_days",
        "enzymaticDegradability": "environmental_impact",
        "cytotoxicitySafe": "cytotoxicity_safe",
        "sterGamma": "sterilization_gamma",
        "sterEto": "sterilization_eto",
        "sterSteam": "sterilization_steam",
        "procFilm": "film_forming",
        "evidenceLevel": "evidence_level",
    }

    rename_dict = {old: new for old, new in column_mapping.items() if old in df.columns and new not in df.columns}
    if rename_dict:
        df = df.rename(columns=rename_dict)

    if "polymer" not in df.columns:
        if "name" in df.columns:
            df["polymer"] = df["name"]
        else:
            df["polymer"] = "Unknown Polymer"

    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    if "biocompatibility" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["biocompatibility"] = df["cytotoxicity_safe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        elif "cytotoxicitySafe" in df.columns:
            df["biocompatibility"] = df["cytotoxicitySafe"].apply(
                lambda x: 9.0 if str(x).strip() in ["1", "1.0", "True", "true"] else 4.0
            )
        else:
            df["biocompatibility"] = 8.0

    if "toxicity_score" not in df.columns:
        if "cytotoxicity_safe" in df.columns:
            df["toxicity_score"] = df["cytotoxicity_safe"].apply(
                lambda x: 8.5 if str(x).strip() in ["1", "1.0", "True", "true"] else 3.0
            )
        else:
            df["toxicity_score"] = 8.0

    if "tensile_strength" not in df.columns:
        if "tensileStrengthMpaMin" in df.columns:
            df["tensile_strength"] = pd.to_numeric(df["tensileStrengthMpaMin"], errors="coerce").fillna(20.0)
        else:
            df["tensile_strength"] = 20.0

    if "elastic_modulus" not in df.columns:
        if "elasticModulusGpaMin" in df.columns:
            df["elastic_modulus"] = pd.to_numeric(df["elasticModulusGpaMin"], errors="coerce").fillna(1.2)
        else:
            df["elastic_modulus"] = 1.2

    if "elongation_pct" not in df.columns:
        if "elongationPctMin" in df.columns:
            df["elongation_pct"] = pd.to_numeric(df["elongationPctMin"], errors="coerce").fillna(45.0)
        else:
            df["elongation_pct"] = 45.0

    if "flexibility" not in df.columns:
        if "elongation_pct" in df.columns:
            df["flexibility"] = pd.to_numeric(df["elongation_pct"], errors="coerce").fillna(45.0) * 0.8
        else:
            df["flexibility"] = 35.0

    if "wvtr" not in df.columns:
        df["wvtr"] = 800.0

    if "oxygen_permeability" not in df.columns:
        if "otr" in df.columns:
            df["oxygen_permeability"] = pd.to_numeric(df["otr"], errors="coerce").fillna(120.0)
        else:
            df["oxygen_permeability"] = 120.0

    if "antimicrobial" not in df.columns:
        df["antimicrobial"] = 0.0

    if "biodegradation_days" not in df.columns:
        if "degradationDaysMin" in df.columns:
            df["biodegradation_days"] = pd.to_numeric(df["degradationDaysMin"], errors="coerce").fillna(60.0)
        else:
            df["biodegradation_days"] = 60.0

    if "environmental_impact" not in df.columns:
        df["environmental_impact"] = 5.0

    if "film_forming" not in df.columns:
        df["film_forming"] = 1.0

    if "sterilization_gamma" not in df.columns:
        df["sterilization_gamma"] = 0.0

    if "sterilization_eto" not in df.columns:
        df["sterilization_eto"] = 0.0

    if "sterilization_steam" not in df.columns:
        df["sterilization_steam"] = 0.0

    if "is_augmented" not in df.columns:
        df["is_augmented"] = 0

    if "evidence_level" not in df.columns:
        df["evidence_level"] = "high"

    return df


def load_dataset_from_mysql(
    table: str = "filtered_polymers",
    force_refresh: bool = False,
) -> tuple[pd.DataFrame | None, dict | None, str | None]:
    """Load the polymer dataset directly from MySQL.

    Results are cached in-process for MYSQL_CACHE_TTL seconds (default 300)
    to prevent redundant queries on every Streamlit rerun. Pass
    force_refresh=True (e.g. from the ↻ Refresh button) to bypass the cache.

    Returns
    -------
    (df, stats, error)
        df    — DataFrame on success, None on failure
        stats — dict of column stats on success, None on failure
        error — human-readable error string on failure, None on success
    """
    # Return cached data if still fresh and not forced
    now = time.time()
    if (
        not force_refresh
        and _dataset_cache["df"] is not None
        and (now - _dataset_cache["loaded_at"]) < _CACHE_TTL_SECONDS
    ):
        return _dataset_cache["df"].copy(), _dataset_cache["stats"], None

    try:
        query = """
        SELECT 
            m.id AS material_id,
            m.name AS polymer,
            m.category AS category,
            m.evidence_level AS evidence_level,
            COALESCE(mp.tensile_strength_mpa_min, 15.0) AS tensile_strength,
            COALESCE(mp.elastic_modulus_gpa_min, 1.2) AS elastic_modulus,
            COALESCE(mp.elongation_pct_min, 45.0) AS elongation_pct,
            COALESCE(mp.elongation_pct_min * 0.8, 35.0) AS flexibility,
            COALESCE(mp.wvtr, 800.0) AS wvtr,
            COALESCE(mp.otr, 120.0) AS oxygen_permeability,
            CASE WHEN mp.cytotoxicity_safe = 1 THEN 9.0 ELSE 4.0 END AS biocompatibility,
            CASE WHEN mp.cytotoxicity_safe = 1 THEN 8.5 ELSE 3.0 END AS toxicity_score,
            CASE WHEN mp.antimicrobial = 1 THEN 1.0 ELSE 0.0 END AS antimicrobial,
            COALESCE(mp.degradation_days_min, 60) AS biodegradation_days,
            CASE WHEN mp.enzymatic_degradability = 1 THEN 9.0 ELSE 5.0 END AS environmental_impact,
            CASE WHEN mp.proc_film = 1 THEN 1.0 ELSE 0.0 END AS film_forming,
            CASE WHEN mp.ster_gamma = 1 THEN 1.0 ELSE 0.0 END AS sterilization_gamma,
            CASE WHEN mp.ster_eto = 1 THEN 1.0 ELSE 0.0 END AS sterilization_eto,
            CASE WHEN mp.ster_steam = 1 THEN 1.0 ELSE 0.0 END AS sterilization_steam,
            0 AS is_augmented,
            1 AS suitability_label,
            0.95 AS data_completeness
        FROM materials m 
        JOIN material_properties mp ON m.id = mp.material_id 
        WHERE m.is_deleted = 0
        """

        with mysql_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

        if not rows:
            return None, None, f"No rows found in MySQL table '{table}'."

        df = pd.DataFrame(rows)

        # Normalise column names: strip whitespace and standardize schema
        df.columns = [str(c).strip() for c in df.columns]
        df = standardize_material_dataframe(df)

        # Coerce numeric columns
        for col in NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ensure all required columns exist (fill missing with NaN)
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan

        # Derive binary suitability_label with at least 2 classes for classification algorithms
        df["suitability_label"] = (
            (df["biocompatibility"] >= 7.5) & (df["toxicity_score"] >= 7.0) & (df["tensile_strength"] >= 15.0)
        ).astype(int)
        if df["suitability_label"].nunique() < 2:
            bio_median = df["biocompatibility"].median()
            df["suitability_label"] = (df["biocompatibility"] > bio_median).astype(int)

        stats = get_dataset_stats(df)

        # Update cache
        _dataset_cache["df"] = df.copy()
        _dataset_cache["stats"] = stats
        _dataset_cache["loaded_at"] = time.time()

        return df, stats, None

    except Exception as exc:
        return None, None, str(exc)


def load_dataset(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate the polymers dataset from a CSV file (legacy/fallback)."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at: {path}")

    df = pd.read_csv(path)

    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    for col in NUMERIC_COLUMNS:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_dataset_auto(csv_path: str | Path | None = None) -> tuple[pd.DataFrame, dict, str]:
    """Try MySQL first, fall back to CSV.

    Returns (df, stats, source) where source is 'mysql' or 'csv'.
    Raises RuntimeError if both sources fail.
    """
    df, stats, err = load_dataset_from_mysql()
    if df is not None:
        return df, stats, "mysql"

    # MySQL failed — try CSV fallback
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "data" / "polymers.csv"

    try:
        df = load_dataset(csv_path)
        stats = get_dataset_stats(df)
        return df, stats, "csv"
    except Exception as csv_err:
        raise RuntimeError(
            f"Both MySQL and CSV loaders failed.\n"
            f"MySQL error: {err}\n"
            f"CSV error: {csv_err}"
        )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_dataset_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute min/max/mean for numeric feature columns."""
    stats: dict[str, dict[str, float]] = {}
    for col in FEATURE_COLUMNS + ["biodegradation_days"]:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) > 0:
                stats[col] = {
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "mean": float(series.mean()),
                }
    return stats


# ---------------------------------------------------------------------------
# Sync: write current MySQL data back to CSV for offline use
# ---------------------------------------------------------------------------

def sync_mysql_to_csv(
    csv_path: str | Path,
    table: str = "filtered_polymers",
) -> dict[str, int]:
    """Pull all rows from MySQL and write to CSV.

    Returns summary: {'fetched': n, 'saved_rows': n}.
    """
    df, _, err = load_dataset_from_mysql(table)
    if df is None:
        raise RuntimeError(f"MySQL sync failed: {err}")

    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)

    return {"fetched": len(df), "saved_rows": len(df)}


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def filter_by_biocompatibility(df: pd.DataFrame, min_val: int) -> pd.DataFrame:
    return df[df["biocompatibility"] >= min_val].copy()


def filter_by_sterilization(
    df: pd.DataFrame,
    gamma: bool = False, eto: bool = False, steam: bool = False,
) -> pd.DataFrame:
    result = df.copy()
    if gamma:
        result = result[result["sterilization_gamma"] == 1]
    if eto:
        result = result[result["sterilization_eto"] == 1]
    if steam:
        result = result[result["sterilization_steam"] == 1]
    return result


def compute_data_completeness(row: pd.Series) -> float:
    """Score 0-1 for how complete a material's data is."""
    key_cols = [
        "tensile_strength", "elastic_modulus", "elongation_pct",
        "flexibility", "wvtr", "oxygen_permeability",
        "biocompatibility", "biodegradation_days",
    ]
    present = sum(1 for c in key_cols if pd.notna(row.get(c)))
    return round(present / len(key_cols), 2)


def ingest_new_material(csv_path: str | Path, row_dict: dict) -> pd.DataFrame:
    """Validate and append a new material to the CSV dataset."""
    path = Path(csv_path)
    df = load_dataset(path) if path.exists() else pd.DataFrame()

    row_dict.setdefault("is_augmented", 0)
    row_dict.setdefault("evidence_level", "low")
    row_dict.setdefault(
        "data_completeness", compute_data_completeness(pd.Series(row_dict))
    )

    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(path, index=False)
    return df


def export_versioned_snapshot(csv_path: str | Path, tag: str | None = None):
    """Save a timestamped copy of the dataset for versioning."""
    import shutil
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No dataset at {path}")
    tag = tag or datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = path.parent / f"polymers_{tag}.csv"
    shutil.copy2(path, dest)
    return dest
