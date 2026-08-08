"""
Audit trail — every recommendation is fully traceable.
Logs input params, model version, SHAP contributions, and final output.
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any

AUDIT_DIR = Path(__file__).parent.parent / "logs" / "audit"


def _ensure_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_decision_trace(
    request_id: str,
    input_params: dict,
    model_version: str,
    safety_rejections: list[dict],
    ranked_materials: list,
    pareto_front: list[str],
    pipeline_metadata: dict,
    latency_report: dict = None,
) -> str:
    """
    Log a complete decision trace for audit.
    Returns the path to the audit log file.
    """
    _ensure_dir()

    # Build top-5 material summaries with SHAP
    top_materials = []
    for m in ranked_materials[:5]:
        entry = {
            "polymer": m.polymer,
            "final_score": m.final_score,
            "confidence": m.confidence,
            "risk_category": m.risk_category,
            "uncertainty": m.uncertainty,
            "is_pareto": m.is_pareto,
            "explanation": m.explanation,
            "warnings": m.warnings,
        }
        if m.shap_values:
            entry["shap_values"] = m.shap_values[:5]  # Top 5 features
        top_materials.append(entry)

    trace = {
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
        "input_parameters": _sanitize(input_params),
        "model_version": model_version,
        "pipeline_steps": pipeline_metadata.get("steps_completed", []),
        "total_materials_evaluated": pipeline_metadata.get("total_materials", 0),
        "safety_rejected_count": len(safety_rejections),
        "safety_rejections": safety_rejections[:10],
        "pareto_front": pareto_front,
        "top_recommendations": top_materials,
        "latency": latency_report or {},
    }

    filename = f"trace_{request_id}.json"
    filepath = AUDIT_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(trace, f, indent=2, default=str)

    # Also append summary to audit_log.csv
    summary = {
        "timestamp": trace["timestamp"],
        "request_id": request_id,
        "top_material": ranked_materials[0].polymer if ranked_materials else "none",
        "top_score": ranked_materials[0].final_score if ranked_materials else 0,
        "top_confidence": ranked_materials[0].confidence if ranked_materials else 0,
        "num_results": len(ranked_materials),
        "num_rejected": len(safety_rejections),
        "model_version": model_version,
    }
    _append_csv(AUDIT_DIR.parent / "audit_log.csv", summary)

    return str(filepath)


def get_audit_history(n: int = 50) -> pd.DataFrame:
    """Return recent audit log entries."""
    log_path = AUDIT_DIR.parent / "audit_log.csv"
    if not log_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(log_path)
    return df.tail(n)


def load_trace(request_id: str) -> dict:
    """Load a specific decision trace."""
    filepath = AUDIT_DIR / f"trace_{request_id}.json"
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {}


def _sanitize(obj):
    """Make object JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


def _append_csv(path: Path, row: dict):
    df = pd.DataFrame([row])
    if path.exists():
        df.to_csv(path, mode='a', header=False, index=False)
    else:
        df.to_csv(path, index=False)
