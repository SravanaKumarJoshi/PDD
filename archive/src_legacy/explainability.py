"""
SHAP explainability module for XGBoost and RandomForest models.
Generates human-readable explanations and Plotly visualizations.
"""
import numpy as np
import pandas as pd
import shap
import plotly.graph_objects as go
from typing import Any

from src.data import FEATURE_COLUMNS

# Human-friendly feature labels
FEATURE_LABELS = {
    "tensile_strength": "Tensile Strength",
    "elastic_modulus": "Elastic Modulus",
    "elongation_pct": "Elongation",
    "flexibility": "Flexibility",
    "wvtr": "Water Vapor Barrier",
    "oxygen_permeability": "Oxygen Permeability",
    "biocompatibility": "Biocompatibility",
    "toxicity_score": "Toxicity Safety",
    "antimicrobial": "Antimicrobial",
    "biodegradation_days": "Biodegradation Time",
    "environmental_impact": "Environmental Impact",
    "film_forming": "Film Forming",
    "sterilization_gamma": "Gamma Sterilization",
    "sterilization_eto": "EtO Sterilization",
    "sterilization_steam": "Steam Sterilization",
}


def compute_shap_values(model, X: pd.DataFrame) -> shap.Explanation:
    """Compute SHAP values for a model and feature matrix."""
    try:
        explainer = shap.TreeExplainer(model)
        return explainer(X)
    except Exception:
        explainer = shap.Explainer(model.predict if hasattr(model, 'predict') else model, X)
        return explainer(X)


def generate_explanation_text(
    shap_vals: np.ndarray,
    feature_names: list[str],
    material_name: str,
    top_n: int = 3,
) -> str:
    """Generate human-readable explanation for a single material."""
    pairs = list(zip(feature_names, shap_vals))
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    parts = []
    for feat, val in pairs[:top_n]:
        label = FEATURE_LABELS.get(feat, feat)
        direction = "high" if val > 0 else "low"
        parts.append(f"{direction} {label} (contribution: {val:+.3f})")

    explanation = f"**{material_name}** selected due to " + ", ".join(parts) + "."
    return explanation


def create_shap_summary_plot(
    shap_values: shap.Explanation,
    feature_names: list[str] = None,
) -> go.Figure:
    """Global feature importance bar chart from SHAP values."""
    feature_names = feature_names or FEATURE_COLUMNS
    if hasattr(shap_values, 'values'):
        vals = shap_values.values
    else:
        vals = np.array(shap_values)

    if vals.ndim == 3:
        vals = vals[:, :, 1]

    mean_abs = np.abs(vals).mean(axis=0)
    labels = [FEATURE_LABELS.get(f, f) for f in feature_names]

    sorted_idx = np.argsort(mean_abs)
    fig = go.Figure(go.Bar(
        x=mean_abs[sorted_idx],
        y=[labels[i] for i in sorted_idx],
        orientation='h',
        marker_color='#6366f1',
    ))
    fig.update_layout(
        title="SHAP Feature Importance (Global)",
        xaxis_title="Mean |SHAP Value|",
        height=500,
        template="plotly_dark",
    )
    return fig


def create_shap_waterfall_data(
    shap_vals: np.ndarray,
    feature_names: list[str],
    base_value: float = 0.5,
) -> go.Figure:
    """Per-material waterfall breakdown."""
    labels = [FEATURE_LABELS.get(f, f) for f in feature_names]
    sorted_idx = np.argsort(np.abs(shap_vals))[::-1]

    colors = ["#22c55e" if v > 0 else "#ef4444" for v in shap_vals[sorted_idx]]

    fig = go.Figure(go.Bar(
        x=shap_vals[sorted_idx],
        y=[labels[i] for i in sorted_idx],
        orientation='h',
        marker_color=colors,
    ))
    fig.update_layout(
        title="SHAP Feature Contributions",
        xaxis_title="SHAP Value (impact on prediction)",
        height=500,
        template="plotly_dark",
    )
    return fig
