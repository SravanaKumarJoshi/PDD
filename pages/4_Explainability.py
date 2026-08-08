"""SHAP Explainability Page — Global and per-material explanations."""
import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "apppp" / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.data import FEATURE_COLUMNS, load_dataset_from_mysql
from src.explainability import (
    compute_shap_values, create_shap_summary_plot,
    create_shap_waterfall_data, generate_explanation_text, FEATURE_LABELS,
)

st.set_page_config(page_title="Explainability", page_icon="🔍", layout="wide")
st.title("🔍 SHAP Explainability Dashboard")
st.markdown("Understand **why** the AI recommends specific materials.")

if "dataset" not in st.session_state or st.session_state.get("dataset_source") != "mysql":
    with st.spinner("Loading materials from MySQL..."):
        df, stats, error = load_dataset_from_mysql()
        if error:
            st.error(f"⚠️ {error}")
            st.info("Ensure MYSQL_HOST / MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD are set in .env")
            st.stop()
        st.session_state["dataset"] = df.copy(deep=True)
        st.session_state["dataset_stats"] = stats
        st.session_state["dataset_source"] = "mysql"

if "xgb_model" not in st.session_state:
    model_path = Path(__file__).parent.parent / "models" / "registry" / "latest" / "model.joblib"
    if model_path.exists():
        import joblib
        st.session_state["xgb_model"] = joblib.load(model_path)
    else:
        st.warning("⚠️ Train models first on the Model Training page.")
        st.stop()

df = st.session_state["dataset"]
model = st.session_state["xgb_model"]
X = df[FEATURE_COLUMNS]

# Compute SHAP
with st.spinner("Computing SHAP values..."):
    try:
        shap_vals = compute_shap_values(model, X)
        vals = getattr(shap_vals, 'values', np.array(shap_vals))
        if vals.ndim == 3:
            vals = vals[:, :, 1]
    except Exception as e:
        st.warning(f"⚠️ Could not compute exact SHAP values: {e}")
        vals = np.zeros((len(X), len(FEATURE_COLUMNS)))
        shap_vals = vals

# Global importance
st.header("🌍 Global Feature Importance")
fig = create_shap_summary_plot(shap_vals, FEATURE_COLUMNS)
st.plotly_chart(fig, use_container_width=True)

st.markdown("""
> Features at the top have the **most influence** on the model's decisions across all materials.
> This shows what the model considers most important when evaluating suitability.
""")

# Per-material explanation
st.divider()
st.header("🔬 Per-Material Explanation")

selected = st.selectbox("Select a material:", df["polymer"].tolist())
idx = df[df["polymer"] == selected].index[0]
# Map to position in X
pos = list(df.index).index(idx)

explanation = generate_explanation_text(vals[pos], FEATURE_COLUMNS, selected)
st.markdown(explanation)

fig = create_shap_waterfall_data(vals[pos], FEATURE_COLUMNS)
st.plotly_chart(fig, use_container_width=True)

# Feature contribution table
st.subheader("Feature Contributions")
contrib_data = []
for i, feat in enumerate(FEATURE_COLUMNS):
    label = FEATURE_LABELS.get(feat, feat)
    contrib_data.append({
        "Feature": label,
        "SHAP Value": round(vals[pos][i], 4),
        "Direction": "✅ Positive" if vals[pos][i] > 0 else "❌ Negative",
        "Actual Value": round(float(X.iloc[pos][feat]), 2),
    })
contrib_df = pd.DataFrame(contrib_data).sort_values("SHAP Value", ascending=False)
st.dataframe(contrib_df, use_container_width=True, hide_index=True)

# Compare materials
st.divider()
st.header("⚖️ Compare Two Materials")
c1, c2 = st.columns(2)
with c1:
    mat_a = st.selectbox("Material A:", df["polymer"].tolist(), key="cmp_a")
with c2:
    mat_b = st.selectbox("Material B:", df["polymer"].tolist(), index=1, key="cmp_b")

if mat_a != mat_b:
    idx_a = list(df.index).index(df[df["polymer"] == mat_a].index[0])
    idx_b = list(df.index).index(df[df["polymer"] == mat_b].index[0])

    diff = vals[idx_a] - vals[idx_b]
    labels = [FEATURE_LABELS.get(f, f) for f in FEATURE_COLUMNS]

    import plotly.graph_objects as go
    sorted_idx = np.argsort(np.abs(diff))[::-1]
    colors = ["#22c55e" if d > 0 else "#ef4444" for d in diff[sorted_idx]]

    fig = go.Figure(go.Bar(
        x=diff[sorted_idx], y=[labels[i] for i in sorted_idx],
        orientation='h', marker_color=colors,
    ))
    fig.update_layout(
        title=f"SHAP Difference: {mat_a} vs {mat_b}",
        xaxis_title="SHAP Value Difference (positive = favors A)",
        height=500, template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

with st.sidebar:
    st.header("📖 About SHAP")
    st.markdown("""
    **SHAP** (SHapley Additive Explanations) shows how each
    feature contributes to a prediction.

    - **Positive values** push toward "suitable"
    - **Negative values** push toward "not suitable"
    - **Larger magnitude** = stronger influence
    """)
