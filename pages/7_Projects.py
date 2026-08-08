"""Projects Page — Manage saved screening results from MySQL."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.results_store import load_results, rename_result, delete_result, get_result_by_name

st.set_page_config(page_title="Projects", page_icon="📁", layout="wide")

# ─── CSS ──────────────────────────────────────────────────────────
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>📁 Saved Projects</h1>
    <p>Manage, review, and restore your AI screening results</p>
</div>
""", unsafe_allow_html=True)

# ─── Handle "view full project" state ────────────────────────────
# When the user clicks "Open Project" we store the project name in session
# state and re-render the page in detail view.

if "viewing_project" in st.session_state:
    # ── DETAIL VIEW ───────────────────────────────────────────────
    project_name = st.session_state["viewing_project"]
    result = get_result_by_name(project_name)

    if result is None:
        st.error(f"Project '{project_name}' not found. It may have been deleted.")
        if st.button("← Back to Projects"):
            del st.session_state["viewing_project"]
            st.rerun()
        st.stop()

    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← Back"):
            del st.session_state["viewing_project"]
            st.rerun()
    with col_title:
        st.subheader(f"📄 {result['name']}")

    try:
        ts = datetime.fromisoformat(result.get("timestamp", "")).strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        ts = "Unknown Date"

    reqs = result.get("requirements", {})
    ranked = result.get("ranked_materials", [])
    meta = result.get("pipeline_metadata", {})
    request_id = result.get("request_id", "N/A")

    # ── Summary metrics ───────────────────────────────────────────
    st.caption(f"Saved: {ts}  |  Pipeline ID: {request_id}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Materials Ranked", len(ranked))
    c2.metric("Application Type", reqs.get("application_type", "N/A"))
    c3.metric("Min Biocompatibility", reqs.get("min_biocompatibility", "N/A"))

    # ── Ranked materials table ────────────────────────────────────
    st.divider()
    st.subheader("🏆 Ranked Materials")

    if not ranked:
        # This should never happen for a properly saved project, but guard anyway.
        st.warning(
            "⚠️ No ranked materials found in this saved project. "
            "This can happen if the project was saved before a screening was run. "
            "Re-run the screening from the **Recommend** page and save again."
        )
    else:
        df_ranked = pd.DataFrame(ranked)

        # Always show core columns; gracefully skip absent ones
        core_cols = ["polymer", "category", "final_score", "confidence",
                     "risk_category", "is_pareto"]
        display_cols = [c for c in core_cols if c in df_ranked.columns]
        extra_cols = [c for c in df_ranked.columns if c not in core_cols
                      and c not in ("explanation", "warnings",
                                    "similar_score_alternatives", "shap_values",
                                    "properties")]
        all_display = display_cols + extra_cols

        st.dataframe(
            df_ranked[all_display].rename(columns={
                "polymer": "Material",
                "category": "Category",
                "final_score": "Score (%)",
                "confidence": "Confidence",
                "risk_category": "Risk",
                "is_pareto": "Pareto ⭐",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # ── Per-material detail ───────────────────────────────────
        st.divider()
        st.subheader("🔬 Material Details")
        for i, mat in enumerate(ranked[:10]):
            polymer = mat.get("polymer", f"Material {i+1}")
            score = mat.get("final_score", 0)
            risk = mat.get("risk_category", "")
            explanation = mat.get("explanation", "")
            warnings = mat.get("warnings", [])
            props = mat.get("properties", {})

            with st.expander(
                f"{'⭐ ' if mat.get('is_pareto') else ''}#{i+1} — {polymer}  "
                f"({score:.1f}%  |  Risk: {risk})"
            ):
                if explanation:
                    st.markdown(f"**AI Explanation:** {explanation}")

                if warnings:
                    for w in warnings:
                        st.warning(w)

                if props:
                    prop_items = {k: v for k, v in props.items() if v is not None}
                    if prop_items:
                        st.markdown("**Properties:**")
                        prop_df = pd.DataFrame(
                            [{"Property": k, "Value": v} for k, v in prop_items.items()]
                        )
                        st.dataframe(prop_df, use_container_width=True, hide_index=True)

    # ── Requirements ──────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Original Requirements")
    st.json(reqs)

    # ── Pipeline metadata ─────────────────────────────────────────
    if meta:
        with st.expander("⚙️ Pipeline Metadata"):
            st.json(meta)

    # ── Export ────────────────────────────────────────────────────
    st.divider()
    if ranked:
        export_df = pd.DataFrame(ranked)
        st.download_button(
            "📥 Export Results as CSV",
            export_df.to_csv(index=False),
            file_name=f"{result['name'].replace(' ', '_')}_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.stop()


# ─── LIST VIEW ────────────────────────────────────────────────────
try:
    results = load_results()
except Exception as exc:
    st.error(f"❌ Failed to load projects from MySQL: {exc}")
    st.info(
        "Make sure MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD are "
        "set in your .env file and the `saved_projects` table exists."
    )
    st.stop()

# Metrics
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Saved Results", len(results))

if not results:
    st.info(
        "No saved results found. Go to the **Recommend** page, run a screening, "
        "and click **Save Results** to save it here."
    )
    st.stop()

st.divider()

# ─── Search & Sort ────────────────────────────────────────────────
st.header("🔍 Search & Organize")
c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    search_query = st.text_input("Search by name", "", placeholder="Enter project name...")
with c2:
    sort_by = st.selectbox("Sort By", ["Timestamp", "Name"])
with c3:
    sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)

filtered_results = [r for r in results if search_query.lower() in r["name"].lower()]

reverse_sort = sort_order == "Descending"
if sort_by == "Name":
    filtered_results.sort(key=lambda x: x["name"].lower(), reverse=reverse_sort)
else:
    filtered_results.sort(key=lambda x: x.get("timestamp", ""), reverse=reverse_sort)

st.markdown(f"**Showing {len(filtered_results)} of {len(results)} results**")

# ─── Project Cards ────────────────────────────────────────────────
for i, result in enumerate(filtered_results):
    name = result["name"]
    try:
        ts = datetime.fromisoformat(result.get("timestamp", "")).strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        ts = "Unknown Date"

    reqs = result.get("requirements", {})
    ranked = result.get("ranked_materials", [])
    top_mats = [m.get("polymer", "Unknown") for m in ranked[:3]]

    with st.container():
        st.markdown("---")
        col_info, col_actions = st.columns([4, 1])

        with col_info:
            st.subheader(f"📄 {name}")
            st.caption(f"Saved: {ts}  |  Application: {reqs.get('application_type', 'N/A')}")
            if top_mats:
                st.markdown(f"**Top Matches:** {', '.join(top_mats)}")
            else:
                # This means ranked_materials was empty when saved — guide the user
                st.warning(
                    "⚠️ No ranked materials stored. "
                    "Re-run the screening and save again to capture results."
                )

            # ── Open full project ──────────────────────────────────
            if st.button(f"📂 Open Project", key=f"open_{i}"):
                st.session_state["viewing_project"] = name
                st.rerun()

        with col_actions:
            edit_mode = st.toggle("✏️ Rename", key=f"edit_toggle_{i}")
            delete_mode = st.toggle("🗑️ Delete", key=f"del_toggle_{i}")

        if edit_mode:
            c_input, c_btn = st.columns([3, 1])
            with c_input:
                new_name = st.text_input(
                    "New name", value=name,
                    key=f"rename_input_{i}", label_visibility="collapsed",
                )
            with c_btn:
                if st.button("Save Name", key=f"rename_btn_{i}", type="primary",
                             use_container_width=True):
                    status = rename_result(name, new_name)
                    if status.success:
                        st.toast(status.message, icon="✅")
                        st.rerun()
                    else:
                        st.error(status.message)

        if delete_mode:
            st.warning(f"Are you sure you want to delete '{name}'?")
            if st.button("Confirm Delete", type="primary", key=f"del_btn_{i}"):
                status = delete_result(name)
                if status.success:
                    st.toast(status.message, icon="✅")
                    st.rerun()
                else:
                    st.error(status.message)

        # ── Quick preview ──────────────────────────────────────────
        with st.expander("👁️ Quick Preview"):
            if ranked:
                prev_df = pd.DataFrame(ranked)
                preview_cols = [c for c in ["polymer", "final_score", "risk_category"]
                                if c in prev_df.columns]
                st.dataframe(prev_df[preview_cols].head(5),
                             hide_index=True, use_container_width=True)
            else:
                st.info("No materials to preview.")
            st.caption("**Requirements summary:**")
            st.json({k: v for k, v in reqs.items() if v is not None and v != ""})

st.markdown("---")
