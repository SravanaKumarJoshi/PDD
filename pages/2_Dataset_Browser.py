"""Dataset Browser — view, filter, and add materials from MySQL."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "apppp" / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.data import load_dataset_from_mysql, get_dataset_stats, ingest_new_material, load_dataset, standardize_material_dataframe
from scripts.train_pipeline import load_data_from_mysql_or_fallback

st.set_page_config(page_title="Dataset Browser", page_icon="📊", layout="wide")
st.title("📊 Dataset Browser")

# ─── Load Dataset ──────────────────────────────────────────────────
if "dataset" not in st.session_state:
    with st.spinner("Loading materials..."):
        df, stats, error = load_dataset_from_mysql()
        if error or df is None or df.empty:
            df = load_data_from_mysql_or_fallback()
            stats = get_dataset_stats(df)
        st.session_state["dataset"] = df.copy(deep=True)
        st.session_state["dataset_stats"] = stats
        st.session_state["dataset_source"] = "mysql"

df = st.session_state["dataset"]
df = standardize_material_dataframe(df)
st.session_state["dataset"] = df

if "is_augmented" not in df.columns:
    df["is_augmented"] = 0

# ─── Metrics ──────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Materials", len(df))
c2.metric("Literature-Sourced", len(df[df["is_augmented"] == 0]) if "is_augmented" in df.columns else len(df))
c3.metric("Categories", df["category"].nunique() if "category" in df.columns else 0)
bio_mean = pd.to_numeric(df["biocompatibility"], errors="coerce").mean() if "biocompatibility" in df.columns else 0.0
c4.metric("Avg Biocompatibility", f"{bio_mean:.1f}/10")

st.divider()

# ─── Filters ──────────────────────────────────────────────────────
st.header("🔍 Filters")
c1, c2, c3, c4 = st.columns(4)

categories_list = sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else []

with c1:
    cat_filter = st.multiselect(
        "Category", ["All"] + categories_list, default=["All"]
    )
with c2:
    evid_filter = st.selectbox("Evidence Level", ["All", "high", "med", "low"])
with c3:
    aug_filter = st.selectbox("Data Source", ["All", "Literature Only", "Augmented Only"])
with c4:
    bio_min = st.slider("Min Biocompatibility", 1, 10, 1)

filtered = df.copy()
if "All" not in cat_filter and cat_filter and "category" in filtered.columns:
    filtered = filtered[filtered["category"].isin(cat_filter)]
if evid_filter != "All" and "evidence_level" in filtered.columns:
    filtered = filtered[filtered["evidence_level"] == evid_filter]
if aug_filter == "Literature Only" and "is_augmented" in filtered.columns:
    filtered = filtered[filtered["is_augmented"] == 0]
elif aug_filter == "Augmented Only" and "is_augmented" in filtered.columns:
    filtered = filtered[filtered["is_augmented"] == 1]
if "biocompatibility" in filtered.columns:
    filtered = filtered[pd.to_numeric(filtered["biocompatibility"], errors="coerce") >= bio_min]

st.info(f"Showing {len(filtered)} of {len(df)} materials")

display_cols = [
    "polymer", "category", "tensile_strength", "elastic_modulus",
    "flexibility", "biocompatibility", "toxicity_score",
    "biodegradation_days", "evidence_level", "is_augmented",
]
display_cols = [c for c in display_cols if c in filtered.columns]

st.dataframe(
    filtered[display_cols].rename(columns={
        "polymer": "Polymer", "category": "Category",
        "tensile_strength": "Tensile (MPa)", "elastic_modulus": "Modulus (GPa)",
        "flexibility": "Flexibility", "biocompatibility": "Biocompat.",
        "toxicity_score": "Toxicity Safety", "biodegradation_days": "Biodeg. Days",
        "evidence_level": "Evidence", "is_augmented": "Augmented",
    }),
    use_container_width=True, hide_index=True,
)

st.download_button(
    "📥 Download Filtered CSV", filtered.to_csv(index=False),
    "filtered_polymers.csv", "text/csv", use_container_width=True,
)

# ─── Stats ────────────────────────────────────────────────────────
st.divider()
st.header("📈 Statistics")
c1, c2 = st.columns(2)
with c1:
    st.subheader("Numeric Properties")
    num_cols = [
        c for c in ["tensile_strength", "elastic_modulus", "flexibility",
                    "biocompatibility", "biodegradation_days"]
        if c in filtered.columns
    ]
    if num_cols:
        numeric_df = filtered[num_cols].apply(pd.to_numeric, errors="coerce")
        st.dataframe(
            numeric_df.describe().T[["min", "mean", "max"]].round(2),
            use_container_width=True,
        )
with c2:
    st.subheader("Category Distribution")
    st.dataframe(filtered["category"].value_counts(), use_container_width=True)

# ─── Add New Material ─────────────────────────────────────────────
# st.divider()
# st.header("➕ Add New Material")
# with st.expander("Submit a new material entry"):
#     with st.form("new_material"):
#         nm_name = st.text_input("Polymer Name")
#         nm_cat = st.text_input("Category")
#         nm_ts = st.number_input("Tensile Strength (MPa)", 0.0, 500.0, 50.0)
#         nm_bio = st.slider("Biocompatibility (1-10)", 1, 10, 7)
#         nm_tox = st.slider("Toxicity Safety (1-10)", 1, 10, 8)
#         nm_biodeg = st.number_input("Biodegradation Days", 1, 1000, 90)
#         nm_doi = st.text_input("Source DOI (optional)")

#         if st.form_submit_button("Add Material"):
#             if nm_name and nm_cat:
#                 csv_path = Path(__file__).parent.parent / "data" / "polymers.csv"
#                 new_row = {
#                     "polymer": nm_name, "category": nm_cat,
#                     "tensile_strength": nm_ts, "elastic_modulus": 1.0,
#                     "elongation_pct": 10.0, "flexibility": 5.0,
#                     "wvtr": 300.0, "oxygen_permeability": 100.0,
#                     "biocompatibility": nm_bio, "toxicity_score": nm_tox,
#                     "antimicrobial": 0, "biodegradation_days": nm_biodeg,
#                     "environmental_impact": 7, "solubility": "medium",
#                     "film_forming": 1, "sterilization_gamma": 0,
#                     "sterilization_eto": 1, "sterilization_steam": 0,
#                     "cost_band": "med", "availability_band": "med",
#                     "evidence_level": "low",
#                     "source_doi": nm_doi or "user_submitted",
#                     "is_augmented": 0, "suitability_label": 0,
#                 }
#                 ingest_new_material(csv_path, new_row)
#                 new_df = load_dataset(csv_path)
#                 st.session_state["dataset"] = new_df
#                 from src.data import get_dataset_stats
#                 st.session_state["dataset_stats"] = get_dataset_stats(new_df)
#                 st.session_state["dataset_source"] = "csv"
#                 st.success(f"✅ Added {nm_name} to local CSV (sync to MySQL via admin tools).")
#                 st.rerun()
#             else:
#                 st.error("Name and category are required.")

# ─── Refresh from MySQL ───────────────────────────────────────────
st.divider()
st.header("🔄 Sync Materials from MySQL")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("↻ Reload from MySQL", use_container_width=True):
        with st.spinner("Reloading materials from MySQL..."):
            df_new, stats_new, err = load_dataset_from_mysql(force_refresh=True)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state["dataset"] = df_new.copy(deep=True)
                st.session_state["dataset_stats"] = stats_new
                st.session_state["dataset_source"] = "mysql"
                st.success(f"✅ Reloaded {len(df_new)} materials from MySQL.")
                st.rerun()

with col2:
    st.caption(
        "Reloads the full material catalog from MySQL. "
        "Any filters above will reset on reload."
    )
