"""Feedback & Retraining Management Page."""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retraining import (
    submit_feedback, approve_pending, get_approved_count,
    should_retrain, get_model_history, validate_new_model,
)

FEEDBACK_DIR = Path(__file__).parent.parent / "feedback"

st.set_page_config(page_title="Feedback", page_icon="💬", layout="wide")
st.title("💬 Feedback & Continuous Learning")
st.markdown("Submit feedback, review pending entries, and trigger model retraining.")

# ─── Submit Feedback ──────────────────────────────────────────────
st.header("📝 Submit Feedback")

with st.form("feedback_form"):
    fb_material = st.text_input("Material Name")
    fb_role = st.selectbox("Your Role", ["doctor", "researcher", "engineer", "admin"])
    fb_type = st.selectbox("Feedback Type", [
        "recommendation_accuracy", "property_correction",
        "new_application", "safety_concern",
    ])
    fb_rating = st.slider("Rating (1-10)", 1, 10, 7)
    fb_confidence = st.slider("How confident are you? (1-5)", 1, 5, 3,
                              help="Low confidence entries go to admin review")
    fb_notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("Submit Feedback")
    if submitted:
        if not fb_material:
            st.error("Material name required.")
        else:
            entry = {
                "material_name": fb_material,
                "user_role": fb_role,
                "feedback_type": fb_type,
                "rating": fb_rating,
                "self_confidence": fb_confidence,
                "notes": fb_notes,
            }
            status = submit_feedback(entry)
            if status == "approved":
                st.success("✅ Feedback accepted and logged!")
            elif status == "pending_review":
                st.warning("⏳ Low confidence — queued for admin review.")
            else:
                st.error("❌ Feedback rejected. Check the requirements.")

# ─── Pending Review (Admin) ───────────────────────────────────────
st.divider()
st.header("🔍 Pending Review Queue")

pending_path = FEEDBACK_DIR / "pending_review.csv"
if pending_path.exists():
    pending_df = pd.read_csv(pending_path)
    if len(pending_df) > 0:
        st.dataframe(pending_df, use_container_width=True, hide_index=True)
        approve_idx = st.number_input("Approve entry index:", 0, len(pending_df) - 1, 0)
        if st.button("✅ Approve Selected"):
            if approve_pending(approve_idx):
                st.success("Approved! Reload to see updates.")
                st.rerun()
    else:
        st.info("No pending reviews.")
else:
    st.info("No pending reviews.")

# ─── Approved Feedback ────────────────────────────────────────────
st.divider()
st.header("📊 Feedback Statistics")

approved_count = get_approved_count()
c1, c2 = st.columns(2)
c1.metric("Approved Feedback", approved_count)
c2.metric("Retrain Threshold", "20 entries")

if should_retrain():
    st.success("✅ Enough feedback collected — retraining recommended!")
    if st.button("🔄 Trigger Model Retraining", type="primary"):
        st.info("Retraining would run here. Visit Model Training page to retrain with updated data.")
else:
    remaining = 20 - approved_count
    st.info(f"Need {remaining} more approved feedback entries before retraining.")

# Approved history
approved_path = FEEDBACK_DIR / "approved_feedback.csv"
if approved_path.exists():
    approved_df = pd.read_csv(approved_path)
    if len(approved_df) > 0:
        with st.expander("View Approved Feedback"):
            st.dataframe(approved_df, use_container_width=True, hide_index=True)

# Model versions
st.divider()
st.header("📦 Model Version History")
history = get_model_history()
if history:
    st.dataframe(pd.DataFrame(history)[["version", "model_type", "timestamp"]],
                 use_container_width=True, hide_index=True)
else:
    st.info("No model versions saved yet.")

with st.sidebar:
    st.header("📖 About Feedback")
    st.markdown("""
    **Validation Rules:**
    - Only verified roles accepted
    - Low confidence (< 3) → admin review
    - Model retraining after 20+ approvals
    - New model validated against old (must not degrade >5%)

    **Why Human-in-the-Loop?**
    - Prevents bad data from corrupting models
    - Ensures quality of training data
    - Maintains clinical reliability
    """)
