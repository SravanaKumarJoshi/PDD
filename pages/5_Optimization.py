"""NSGA-II Pareto Front Explorer."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.genetic_algorithm import run_nsga2
from src.data import load_dataset_from_mysql

st.set_page_config(page_title="Optimization", page_icon="🎯", layout="wide")
st.title("🎯 Multi-Objective Optimization")
st.markdown("Explore Pareto-optimal trade-offs between strength, biodegradability, and biocompatibility.")

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

df = st.session_state["dataset"]

# Config
st.header("⚙️ Optimization Settings")
c1, c2, c3 = st.columns(3)
with c1:
    top_n = st.slider("Top-N candidates", 5, 50, 15)
with c2:
    n_gen = st.slider("Generations", 10, 200, 50)
with c3:
    min_bio = st.slider("Min Biocompatibility Filter", 1, 10, 6)

if st.button("🧬 Run NSGA-II Optimization", type="primary", use_container_width=True):
    filtered = df[df["biocompatibility"] >= min_bio].copy()
    filtered = filtered.sort_values("biocompatibility", ascending=False).head(top_n)

    candidates = filtered.to_dict("records")

    with st.spinner(f"Running NSGA-II on {len(candidates)} candidates for {n_gen} generations..."):
        result = run_nsga2(candidates, n_generations=n_gen)

    pareto_idx = result["pareto_indices"]
    pareto_objs = result["pareto_objectives"]

    st.success(f"✅ Found {len(pareto_idx)} Pareto-optimal materials")

    # 3D scatter plot
    st.header("📊 Pareto Front Visualization")

    all_strength = [min(c.get("tensile_strength", 0) / 300, 1.0) for c in candidates]
    all_biodeg = [1 - min(c.get("biodegradation_days", 365) / 730, 1.0) for c in candidates]
    all_biocomp = [min(c.get("biocompatibility", 0) / 10, 1.0) for c in candidates]
    all_names = [c["polymer"] for c in candidates]

    is_pareto = [i in pareto_idx for i in range(len(candidates))]

    fig = go.Figure()

    # Non-pareto points
    non_p = [i for i in range(len(candidates)) if not is_pareto[i]]
    if non_p:
        fig.add_trace(go.Scatter3d(
            x=[all_strength[i] for i in non_p],
            y=[all_biodeg[i] for i in non_p],
            z=[all_biocomp[i] for i in non_p],
            mode='markers',
            marker=dict(size=5, color='#64748b', opacity=0.5),
            text=[all_names[i] for i in non_p],
            name="Non-Pareto",
        ))

    # Pareto points
    fig.add_trace(go.Scatter3d(
        x=[all_strength[i] for i in pareto_idx],
        y=[all_biodeg[i] for i in pareto_idx],
        z=[all_biocomp[i] for i in pareto_idx],
        mode='markers',
        marker=dict(size=10, color='#22c55e', symbol='diamond'),
        text=[all_names[i] for i in pareto_idx],
        name="Pareto-Optimal",
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="Strength (normalized)",
            yaxis_title="Biodegradability (normalized)",
            zaxis_title="Biocompatibility (normalized)",
        ),
        title="Pareto Front: 3 Objectives",
        height=600,
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Pareto materials table
    st.header("⭐ Pareto-Optimal Materials")
    pareto_data = []
    for i in pareto_idx:
        c = candidates[i]
        pareto_data.append({
            "Polymer": c["polymer"],
            "Tensile (MPa)": c.get("tensile_strength", "N/A"),
            "Biodeg. Days": c.get("biodegradation_days", "N/A"),
            "Biocompat.": c.get("biocompatibility", "N/A"),
            "Category": c.get("category", ""),
        })
    st.dataframe(pd.DataFrame(pareto_data), use_container_width=True, hide_index=True)

    st.markdown("""
    > **Pareto-optimal** means no other material is better in ALL three objectives simultaneously.
    > These materials represent the best trade-offs between strength, biodegradability, and biocompatibility.
    """)

with st.sidebar:
    st.header("📖 About NSGA-II")
    st.markdown("""
    **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) finds
    solutions that are optimal across multiple competing objectives.

    **3 Objectives:**
    - ↑ Tensile Strength
    - ↑ Biodegradability
    - ↑ Biocompatibility

    **Pareto Front** = set of solutions where improving one objective
    requires worsening another.
    """)
