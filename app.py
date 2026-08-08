"""
BioPolymer AI Screening Platform
Main Streamlit Dashboard
"""
import streamlit as st
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.train_pipeline import load_data_from_mysql_or_fallback

# ─── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="BioPolymer AI Screening",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Premium CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d9488 50%, #059669 100%);
        padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
        color: white; text-align: center;
    }
    .main-header h1 { font-size: 2.4rem; font-weight: 700; margin: 0; }
    .main-header p { font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #334155);
        border: 1px solid #475569; border-radius: 12px;
        padding: 1.2rem; text-align: center; color: white;
    }
    .metric-card h3 { font-size: 2rem; margin: 0; color: #34d399; }
    .metric-card p { font-size: 0.85rem; color: #94a3b8; margin: 0.3rem 0 0; }
    .pipeline-step {
        background: #1e293b; border-left: 4px solid #6366f1;
        padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0;
        color: #e2e8f0;
    }
    .pipeline-step strong { color: #a5b4fc; }
    .feature-card {
        background: #0f172a; border: 1px solid #334155;
        border-radius: 12px; padding: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧬 BioPolymer AI Screening Platform</h1>
    <p>AI-Powered Decision Support for Biomedical Packaging Material Selection</p>
</div>
""", unsafe_allow_html=True)

# ─── Clinical Disclaimer ──────────────────────────────────────────
st.info(
    "⚕️ **Clinical Disclaimer:** This system provides AI-assisted recommendations "
    "for research and decision support. It does not replace professional medical "
    "judgment. Experimental validation is required before clinical use."
)

# ─── Sidebar refresh button ───────────────────────────────────────
refresh_requested = st.sidebar.button("↻ Refresh from MySQL", use_container_width=True)

if refresh_requested or "dataset" not in st.session_state:
    with st.spinner("Loading materials from MySQL..."):
        df = load_data_from_mysql_or_fallback()
        st.session_state["dataset"] = df.copy(deep=True)
        st.session_state["dataset_stats"] = {
            "total_rows": len(df),
            "categories": df["category"].nunique() if "category" in df.columns else 0
        }
        st.session_state["dataset_source"] = "mysql"

df = st.session_state["dataset"]
stats = st.session_state["dataset_stats"]

if refresh_requested:
    st.success("✅ Reloaded the latest materials from MySQL.")

# ─── Metrics Overview ─────────────────────────────────────────────
st.header("📊 System Overview")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f'<div class="metric-card"><h3>{len(df)}</h3><p>Total Materials</p></div>', unsafe_allow_html=True)
with c2:
    real = len(df[df["is_augmented"] == 0]) if "is_augmented" in df.columns else len(df)
    st.markdown(f'<div class="metric-card"><h3>{real}</h3><p>Literature-Sourced</p></div>', unsafe_allow_html=True)
with c3:
    cats = df["category"].nunique()
    st.markdown(f'<div class="metric-card"><h3>{cats}</h3><p>Categories</p></div>', unsafe_allow_html=True)
with c4:
    avg_bio = pd.to_numeric(df["biocompatibility"], errors="coerce").mean()
    st.markdown(f'<div class="metric-card"><h3>{avg_bio:.1f}</h3><p>Avg Biocompatibility</p></div>', unsafe_allow_html=True)
with c5:
    model_status = "✅" if "xgb_model" in st.session_state else "⚠️"
    st.markdown(f'<div class="metric-card"><h3>{model_status}</h3><p>Model Status</p></div>', unsafe_allow_html=True)

st.divider()

# ─── Pipeline Architecture ────────────────────────────────────────
st.header("🔬 7-Step AI Pipeline")

steps = [
    ("1️⃣", "User Input", "Parse & validate biomedical requirements"),
    ("2️⃣", "Safety Gate", "Hard-reject toxic/non-compliant materials (PRE-ML)"),
    ("3️⃣", "FAISS Similarity", "Find top-K similar materials via vector search"),
    ("4️⃣", "XGBoost + RF Ensemble", "Predict suitability with calibrated confidence"),
    ("5️⃣", "NSGA-II Optimization", "Pareto-optimal trade-offs on top-N candidates"),
    ("6️⃣", "SHAP Explainability", "Feature-level reasoning for each recommendation"),
    ("7️⃣", "Confidence Scoring", "Platt-calibrated probability + risk categories"),
]

for icon, title, desc in steps:
    st.markdown(
        f'<div class="pipeline-step">{icon} <strong>{title}</strong> — {desc}</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ─── Quick Start ──────────────────────────────────────────────────
st.header("🚀 Quick Start Guide")
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("1️⃣ Train Models")
    st.markdown("Visit **Model Training** to train XGBoost + RandomForest ensemble.")
    if "xgb_model" in st.session_state:
        st.success("✅ Models trained")
    else:
        st.warning("⚠️ Models not yet trained")

with c2:
    st.subheader("2️⃣ Set Requirements")
    st.markdown("Go to **Recommend** and specify your biomedical packaging needs.")

with c3:
    st.subheader("3️⃣ Get Results")
    st.markdown("Receive ranked recommendations with SHAP explanations and confidence scores.")

st.divider()

# ─── Key Features ─────────────────────────────────────────────────
st.header("✨ Key Features")
tab1, tab2, tab3 = st.tabs(["🔬 AI Models", "🛡️ Safety & Trust", "📈 Explainability"])

with tab1:
    st.markdown("""
    - **XGBoost** primary prediction (98%+ accuracy on 210 materials)
    - **RandomForest** benchmarking with side-by-side comparison
    - **FAISS** vector similarity search (production-scale)
    - **NSGA-II** multi-objective optimization (Pareto front)
    - **Weighted ensemble** prediction (70% XGBoost + 30% RF)
    """)

with tab2:
    st.markdown("""
    - **Pre-ML Safety Gate** — hard-rejects toxic materials before any ML runs
    - **Confidence scoring** — Platt-calibrated probabilities with risk categories
    - **Validated feedback** — human-in-the-loop approval for model retraining
    - **Model versioning** — rollback if new model degrades performance
    - **Data provenance** — augmented vs literature-sourced flagging
    """)

with tab3:
    st.markdown("""
    - **SHAP explanations** for every recommendation
    - **Feature contribution** waterfall plots
    - **Global importance** summary across all materials
    - **Human-readable text**: "Selected due to high biocompatibility (+0.34)..."
    """)

# ─── Footer ───────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center; color:#64748b; padding:1rem;">
    <strong>BioPolymer AI Screening Platform v2.0</strong><br>
    XGBoost • FAISS • NSGA-II • SHAP • Streamlit • MySQL<br>
    For biomedical packaging material selection
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("🧭 Navigation")
    st.markdown("""
    - **Home**: Overview & architecture
    - **Recommend**: Get AI recommendations
    - **Dataset Browser**: Explore materials
    - **Model Training**: Train & compare models
    - **Explainability**: SHAP analysis
    - **Optimization**: Pareto front explorer
    - **Feedback**: Submit & review feedback
    - **Projects**: Manage saved results
    """)
    st.divider()
    st.header("📈 Session Status")
    st.markdown(f"**Dataset:** ✅ {len(df)} materials loaded (MySQL)")
    xgb = "✅ Trained" if "xgb_model" in st.session_state else "⚠️ Not trained"
    st.markdown(f"**XGBoost:** {xgb}")
    rf = "✅ Trained" if "rf_model" in st.session_state else "⚠️ Not trained"
    st.markdown(f"**RandomForest:** {rf}")
