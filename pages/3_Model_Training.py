"""Model Training & Comparison Page — XGBoost + RandomForest side-by-side."""
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

from src.xgboost_model import train_xgboost, get_feature_importance
from src.model import train_model as train_rf, compare_models
from src.retraining import save_model_version, get_model_history
from src.explainability import compute_shap_values, create_shap_summary_plot
from src.data import FEATURE_COLUMNS, load_dataset_from_mysql, get_dataset_stats  # MySQL-only loader
from src.evaluation import (
    run_strict_validation, plot_roc_curve,
    plot_confusion_matrix_fig, plot_overfit_chart,
)
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="Model Training", page_icon="🤖", layout="wide")

st.title("🤖 Model Training & Comparison")
st.markdown("Train XGBoost + RandomForest ensemble and compare performance.")

# Auto-load dataset if not already in session (e.g. navigated here directly)
if "dataset" not in st.session_state or st.session_state.get("dataset_source") != "mysql":
    with st.spinner("Loading dataset from MySQL..."):
        try:
            _df, _stats, error = load_dataset_from_mysql()
            if error:
                raise RuntimeError(error)
            st.session_state["dataset"] = _df
            st.session_state["dataset_stats"] = _stats
            st.session_state["dataset_source"] = "mysql"
        except Exception as e:
            st.error(f"❌ Failed to load dataset from MySQL: {e}")
            st.info("Ensure MYSQL_HOST, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD are set in .env")
            st.stop()

df = st.session_state["dataset"]

# ─── Config ───────────────────────────────────────────────────────
st.header("⚙️ Training Configuration")
c1, c2, c3 = st.columns(3)
with c1:
    test_size = st.slider("Test Size (%)", 10, 50, 30, 5) / 100
with c2:
    random_state = st.number_input("Random Seed", 0, 1000, 42)
with c3:
    cv_folds = st.selectbox("CV Folds", [3, 5, 10], index=1)

# ─── Train ────────────────────────────────────────────────────────
if st.button("🚀 Train Both Models", type="primary", use_container_width=True):
    with st.spinner("Training XGBoost..."):
        xgb_model, xgb_metrics = train_xgboost(
            df, test_size=test_size, random_state=random_state, cv_folds=cv_folds
        )
        st.session_state["xgb_model"] = xgb_model
        st.session_state["xgb_metrics"] = xgb_metrics

    with st.spinner("Training RandomForest..."):
        rf_model, rf_metrics = train_rf(
            df, test_size=test_size, random_state=random_state, cv_folds=cv_folds
        )
        st.session_state["rf_model"] = rf_model
        st.session_state["rf_metrics"] = rf_metrics
        # Keep backward compat key
        st.session_state["model"] = rf_model
        st.session_state["metrics"] = rf_metrics

    # Save versions
    save_model_version(xgb_model, "xgboost", xgb_metrics)
    save_model_version(rf_model, "random_forest", rf_metrics)

    st.success("✅ Both models trained and saved!")

    # Strict validation
    st.divider()
    st.header("🔒 Strict Model Validation (Hold-Out Test)")
    st.markdown("True hold-out set never seen during training or CV.")

    with st.spinner("Running strict XGBoost validation..."):
        xgb_val = run_strict_validation(
            XGBClassifier,
            {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
             "subsample": 0.7, "colsample_bytree": 0.7,
             "reg_alpha": 0.1, "reg_lambda": 1.0, "min_child_weight": 3,
             "eval_metric": "logloss", "random_state": random_state},
            df, cv_folds=cv_folds, random_state=random_state,
        )
        st.session_state["xgb_validation"] = xgb_val

    # Overfitting check
    if xgb_val["overfit_warning"]:
        st.error(xgb_val["overfit_warning"])
    else:
        st.success("✅ No overfitting detected")

    # Hold-out metrics
    hm = xgb_val["holdout_metrics"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hold-Out Accuracy", f"{hm['accuracy']:.1%}")
    c2.metric("Hold-Out F1", f"{hm['f1']:.1%}")
    c3.metric("Hold-Out ROC-AUC", f"{hm['roc_auc']:.3f}")
    cv_s = xgb_val["cv_summary"]
    c4.metric("CV Accuracy", f"{cv_s['accuracy_mean']:.3f} ± {cv_s['accuracy_std']:.3f}")

    # Per-fold metrics
    st.subheader("Per-Fold Cross-Validation")
    fold_df = pd.DataFrame(xgb_val["fold_metrics"])
    st.dataframe(fold_df, use_container_width=True, hide_index=True)

    # Overfit chart
    fig_overfit = plot_overfit_chart(xgb_val["fold_metrics"])
    st.plotly_chart(fig_overfit, use_container_width=True)

    # ROC curve
    c1, c2 = st.columns(2)
    with c1:
        fig_roc = plot_roc_curve(xgb_val["holdout_y_true"], xgb_val["holdout_y_proba"])
        st.plotly_chart(fig_roc, use_container_width=True)
    with c2:
        fig_cm = plot_confusion_matrix_fig(hm["confusion_matrix"])
        st.plotly_chart(fig_cm, use_container_width=True)

# ─── Results ──────────────────────────────────────────────────────
if "xgb_metrics" in st.session_state and "rf_metrics" in st.session_state:
    xm = st.session_state["xgb_metrics"]
    rm = st.session_state["rf_metrics"]

    st.divider()
    st.header("📊 Model Comparison")

    comparison = compare_models(xm, rm)

    # Metrics table
    rows = []
    for metric_name, vals in comparison.items():
        rows.append({
            "Metric": metric_name.replace("_", " ").title(),
            "XGBoost": f"{vals['xgboost']:.3f}",
            "RandomForest": f"{vals['random_forest']:.3f}",
            "Winner": "🏆 " + vals["winner"].replace("_", " ").title(),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Detailed metrics
    st.divider()
    st.header("📈 Detailed Metrics")

    tab1, tab2 = st.tabs(["XGBoost", "RandomForest"])
    for tab, name, metrics in [(tab1, "XGBoost", xm), (tab2, "RandomForest", rm)]:
        with tab:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Accuracy", f"{metrics['accuracy']:.1%}")
            c2.metric("Precision", f"{metrics['precision']:.1%}")
            c3.metric("Recall", f"{metrics['recall']:.1%}")
            c4.metric("F1 Score", f"{metrics['f1']:.1%}")

            c1, c2 = st.columns(2)
            c1.metric("CV Mean", f"{metrics['cv_mean']:.3f}")
            c2.metric("CV Std", f"±{metrics['cv_std']:.3f}")

    # Feature Importance
    st.divider()
    st.header("🎯 Feature Importance (XGBoost)")

    xgb_model = st.session_state["xgb_model"]
    importance = get_feature_importance(xgb_model)
    imp_df = pd.DataFrame([
        {"Feature": k, "Importance": v} for k, v in importance.items()
    ]).sort_values("Importance", ascending=False)
    st.bar_chart(imp_df.set_index("Feature"), use_container_width=True)

    # SHAP Global
    st.divider()
    st.header("🔍 SHAP Global Feature Importance")
    with st.spinner("Computing SHAP values..."):
        try:
            X = df[FEATURE_COLUMNS]
            shap_vals = compute_shap_values(xgb_model, X)
            fig = create_shap_summary_plot(shap_vals, FEATURE_COLUMNS)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"SHAP computation failed: {e}")

    # Model History
    st.divider()
    st.header("📦 Model Version History")
    history = get_model_history()
    if history:
        hist_df = pd.DataFrame(history)
        st.dataframe(hist_df[["version", "model_type", "timestamp"]], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("No saved model versions yet.")

else:
    st.info("👆 Click 'Train Both Models' to begin.")

# Sidebar
with st.sidebar:
    st.header("💡 Tips")
    st.markdown("""
    - **XGBoost** is the primary model (higher accuracy)
    - **RandomForest** serves as benchmark
    - **Ensemble** uses 70% XGBoost + 30% RF
    - Models are versioned and persisted
    - SHAP shows why the model makes decisions
    """)
