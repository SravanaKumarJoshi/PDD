"""Material Recommendation Page — Full 7-Step Pipeline."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.ml.config import FEATURE_COLUMNS
from scripts.train_pipeline import load_data_from_mysql_or_fallback

st.set_page_config(page_title="Recommend", page_icon="🔬", layout="wide")

st.title("🔬 AI-Powered Material Recommendation")
st.markdown("Get ranked polysaccharide recommendations with SHAP explanations and confidence scores.")

st.info(
    "⚕️ **Disclaimer:** This system provides AI-assisted recommendations for "
    "research and decision support. It does not replace professional medical judgment. "
    "Experimental validation is required before clinical use."
)

# ─── Load dataset from MySQL ──────────────────────────────────────
if "dataset" not in st.session_state:
    with st.spinner("Loading materials from MySQL..."):
        df = load_data_from_mysql_or_fallback()
        st.session_state["dataset"] = df.copy(deep=True)
        st.session_state["dataset_source"] = "mysql"
            st.info(
                "💡 Ensure MySQL is running and MYSQL_HOST / MYSQL_DATABASE / "
                "MYSQL_USER / MYSQL_PASSWORD are set in your .env file."
            )
            st.stop()
        st.session_state["dataset"] = df.copy(deep=True)
        st.session_state["dataset_stats"] = stats
        st.session_state["dataset_source"] = "mysql"

if "xgb_model" not in st.session_state:
    st.warning("⚠️ Models not trained. Visit **Model Training** page first.")
    st.info("You can still run recommendations without ML (similarity-only mode).")

df = st.session_state["dataset"]
stats = st.session_state.get("dataset_stats") or get_dataset_stats(df)

# ─── Requirements Form ────────────────────────────────────────────
st.header("📋 Your Requirements")
c1, c2 = st.columns(2)

with c1:
    st.subheader("Application & Safety")
    app_type = st.selectbox("Application Type", [
        "Wound dressing packaging", "Drug delivery film",
        "Implant sterile covers", "Tissue scaffold wraps",
        "Surgical instrument packaging", "Blood bag components",
    ])
    min_biocompat = st.slider("Min Biocompatibility (1-10)", 1, 10, 7)
    requires_antimicrobial = st.toggle("Antimicrobial Required", False)

    st.subheader("Sterilization")
    ster_gamma = st.checkbox("Gamma Radiation")
    ster_eto = st.checkbox("Ethylene Oxide (EtO)")
    ster_steam = st.checkbox("Steam/Autoclave")

with c2:
    st.subheader("Target Properties")
    t_tensile = st.number_input(
        "Tensile Strength (MPa)", 0.0, 300.0,
        float(stats.get("tensile_strength", {}).get("mean", 50.0)), 5.0,
    )
    t_modulus = st.number_input("Elastic Modulus (GPa)", 0.0, 30.0, 2.0, 0.5)
    t_flex = st.slider("Flexibility (1-10)", 1.0, 10.0, 7.0, 0.5)
    t_wvtr = st.number_input("WVTR (g/m²/day)", 0.0, 10000.0, 300.0, 50.0)
    t_o2 = st.number_input("O₂ Permeability", 0.0, 10000.0, 100.0, 10.0)

    st.subheader("Biodegradation")
    biodeg_min = int(stats.get("biodegradation_days", {}).get("min", 1))
    biodeg_max = int(stats.get("biodegradation_days", {}).get("max", 730))
    biodeg = st.slider("Acceptable Days", biodeg_min, biodeg_max, (30, 180))

# ─── Run Pipeline ─────────────────────────────────────────────────
if st.button("🔍 Find Recommendations", type="primary", use_container_width=True):
    requirements = {
        "application_type": app_type,
        "target_tensile_strength": t_tensile,
        "target_elastic_modulus": t_modulus,
        "target_flexibility": t_flex,
        "target_wvtr": t_wvtr,
        "target_oxygen_permeability": t_o2,
        "biodeg_min": biodeg[0],
        "biodeg_max": biodeg[1],
        "min_biocompatibility": min_biocompat,
        "requires_antimicrobial": requires_antimicrobial,
        "sterilization_gamma": ster_gamma,
        "sterilization_eto": ster_eto,
        "sterilization_steam": ster_steam,
    }

    st.session_state["last_requirements"] = requirements

    with st.spinner("Running 7-step AI pipeline..."):
        result = run_full_pipeline(
            df, requirements,
            xgb_model=st.session_state.get("xgb_model"),
            rf_model=st.session_state.get("rf_model"),
            dataset_stats=stats,
        )

    st.session_state["last_pipeline_result"] = result

# ─── Render results ───────────────────────────────────────────────
if "last_pipeline_result" in st.session_state:
    result = st.session_state["last_pipeline_result"]
    requirements = st.session_state.get("last_requirements", {})

    if result.input_validation_warnings:
        for w in result.input_validation_warnings:
            st.warning(w)

    meta = result.pipeline_metadata
    if "errors" in meta:
        for e in meta["errors"]:
            st.error(f"❌ {e}")
        st.stop()

    steps_done = len(meta.get("steps_completed", []))
    st.success(f"✅ Pipeline complete — {steps_done}/7 steps executed (ID: {result.request_id})")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Materials Evaluated", meta.get("total_materials", 0))
    c2.metric("Safety Rejected", len(result.safety_rejections))
    c3.metric("Pareto Optimal", meta.get("pareto_count", 0))
    latency = result.latency_report
    total_ms = latency.get("total_ms", 0)
    c4.metric("Latency", f"{total_ms:.0f}ms {'✅' if total_ms < 1000 else '⚠️'}")

    if result.safety_rejections:
        with st.expander(f"🛡️ {len(result.safety_rejections)} Materials Safety-Rejected"):
            for rej in result.safety_rejections[:10]:
                st.markdown(f"**{rej['polymer']}**: {', '.join(rej['reasons'])}")

    if not result.ranked_materials:
        st.error("❌ No materials passed safety filters. Adjust requirements.")
        st.stop()

    st.divider()
    top = result.ranked_materials[0]
    st.header(f"🏆 Best Match: {top.polymer}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Suitability Score", f"{top.final_score:.1f}%")
    c2.metric("Confidence", f"{top.confidence:.2f}")
    c3.metric("Risk", top.risk_category)

    if top.is_pareto:
        st.info("⭐ This material is Pareto-optimal")

    if top.explanation:
        st.markdown(top.explanation)

    if top.similar_score_alternatives:
        alt_list = ", ".join(top.similar_score_alternatives)
        st.warning(f"⚖️ **Similar scores detected.** Consider also: {alt_list}.")

    if top.warnings:
        for w in top.warnings:
            st.warning(w)

    st.divider()
    st.header("📊 Top Recommendations")

    table_data = []
    for m in result.ranked_materials[:10]:
        table_data.append({
            "Polymer": ("⭐ " if m.is_pareto else "") + m.polymer,
            "Score": f"{m.final_score:.1f}%",
            "Confidence": f"{m.confidence:.2f}",
            "Risk": m.risk_category,
            "Category": m.category,
            "Biocompat.": m.properties.get("biocompatibility", ""),
            "Tensile": m.properties.get("tensile_strength", ""),
            "Warnings": "; ".join(m.warnings) if m.warnings else "",
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    st.divider()
    st.header("🔍 SHAP Explanations")
    for m in result.ranked_materials[:5]:
        if m.explanation:
            with st.expander(f"{m.polymer} — Score: {m.final_score:.1f}%"):
                st.markdown(m.explanation)
                if m.shap_values:
                    from src.explainability import create_shap_waterfall_data, FEATURE_LABELS
                    import numpy as np
                    fig = create_shap_waterfall_data(np.array(m.shap_values), FEATURE_COLUMNS)
                    st.plotly_chart(fig, use_container_width=True)

    if result.pareto_front:
        st.divider()
        st.header("🎯 Pareto-Optimal Materials")
        pareto_mats = [m for m in result.ranked_materials if m.is_pareto]
        st.markdown(f"**{len(pareto_mats)} materials** on the Pareto front:")
        for m in pareto_mats:
            st.markdown(
                f"- **{m.polymer}** — Score: {m.final_score:.1f}%, "
                f"Tensile: {m.properties.get('tensile_strength', 'N/A')}, "
                f"Biodeg: {m.properties.get('biodegradation_days', 'N/A')} days, "
                f"Biocompat: {m.properties.get('biocompatibility', 'N/A')}/10"
            )

    # ─── Save Results ─────────────────────────────────────────────
    st.divider()
    st.header("💾 Save Screening Results")

    save_name = st.text_input(
        "Result Name",
        value="",
        placeholder="e.g. Wound Dressing - High Biocompat Run",
        key="save_result_name",
    )

    if st.button("💾 Save Results", type="primary", use_container_width=True):
        if not save_name.strip():
            st.error("Please enter a name before saving.")
        else:
            # Serialize each ranked material into a plain dict for storage
            materials_data = []
            for m in result.ranked_materials:
                materials_data.append({
                    "polymer": m.polymer,
                    "category": m.category,
                    "final_score": m.final_score,
                    "confidence": m.confidence,
                    "risk_category": m.risk_category,
                    "uncertainty": m.uncertainty,
                    "explanation": m.explanation,
                    "is_pareto": m.is_pareto,
                    "warnings": m.warnings,
                    "properties": m.properties,
                    "similar_score_alternatives": m.similar_score_alternatives,
                    "shap_values": m.shap_values if hasattr(m, "shap_values") else None,
                })

            status = save_result(
                name=save_name,
                ranked_materials=materials_data,
                requirements=requirements,
                request_id=result.request_id,
                pipeline_metadata=result.pipeline_metadata,
            )

            if status.success:
                st.success(f"✅ {status.message}")
            elif status.conflicting_name:
                st.error(f"❌ {status.message}")
                st.info("Use a different name or go to the Projects page to delete the existing result.")
            else:
                st.error(f"❌ {status.message}")

with st.sidebar:
    st.header("ℹ️ Pipeline Steps")
    st.markdown("""
    1. **Safety Gate** — reject unsafe materials
    2. **FAISS** — similarity search
    3. **XGBoost+RF** — ensemble prediction
    4. **NSGA-II** — Pareto optimization
    5. **SHAP** — feature explanations
    6. **Confidence** — calibrated scores
    """)
