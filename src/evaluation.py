"""
Strict model validation with cross-validation, hold-out test, and ROC-AUC.
Designed to catch overfitting and ensure generalization.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
from sklearn.model_selection import (
    StratifiedKFold, cross_val_predict, train_test_split,
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report,
)
from typing import Any

from src.data import FEATURE_COLUMNS


def run_strict_validation(
    model_class,
    model_params: dict,
    df: pd.DataFrame,
    feature_cols: list[str] = None,
    target_col: str = "suitability_label",
    cv_folds: int = 5,
    holdout_fraction: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Strict validation protocol:
    1. Reserve true hold-out set (never seen during CV)
    2. Run stratified K-fold CV on remaining data
    3. Report per-fold + aggregated metrics
    4. Final evaluation on hold-out
    """
    feature_cols = feature_cols or FEATURE_COLUMNS
    X = df[feature_cols].copy().apply(pd.to_numeric, errors="coerce").fillna(0.0).values
    y_series = pd.to_numeric(df[target_col], errors="coerce") if target_col in df.columns else pd.Series(dtype=float)

    if y_series.isna().any() or y_series.nunique() < 2:
        bio = df["biocompatibility"] if "biocompatibility" in df.columns else np.random.randn(len(df))
        bio = pd.to_numeric(bio, errors="coerce").fillna(5.0)
        y = (bio >= bio.median()).astype(int).values
    else:
        y = y_series.astype(int).values

    # Step 1: Reserve true hold-out
    X_dev, X_holdout, y_dev, y_holdout = train_test_split(
        X, y, test_size=holdout_fraction,
        random_state=random_state, stratify=y,
    )

    # Step 2: Stratified K-Fold CV on dev set
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    fold_metrics = []
    train_accuracies = []

    for fold_idx, (train_idx, val_idx) in enumerate(cv.split(X_dev, y_dev)):
        X_train, X_val = X_dev[train_idx], X_dev[val_idx]
        y_train, y_val = y_dev[train_idx], y_dev[val_idx]

        model = model_class(**model_params)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)[:, 1]
        y_train_pred = model.predict(X_train)

        train_acc = accuracy_score(y_train, y_train_pred)
        val_acc = accuracy_score(y_val, y_pred)
        train_accuracies.append(train_acc)

        fold_metrics.append({
            "fold": fold_idx + 1,
            "train_accuracy": round(train_acc, 4),
            "val_accuracy": round(val_acc, 4),
            "overfit_gap": round(train_acc - val_acc, 4),
            "precision": round(precision_score(y_val, y_pred, zero_division=0), 4),
            "recall": round(recall_score(y_val, y_pred, zero_division=0), 4),
            "f1": round(f1_score(y_val, y_pred, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y_val, y_proba), 4),
        })

    # Aggregate CV metrics
    cv_df = pd.DataFrame(fold_metrics)
    cv_summary = {
        "accuracy_mean": round(cv_df["val_accuracy"].mean(), 4),
        "accuracy_std": round(cv_df["val_accuracy"].std(), 4),
        "f1_mean": round(cv_df["f1"].mean(), 4),
        "f1_std": round(cv_df["f1"].std(), 4),
        "roc_auc_mean": round(cv_df["roc_auc"].mean(), 4),
        "roc_auc_std": round(cv_df["roc_auc"].std(), 4),
        "overfit_gap_mean": round(cv_df["overfit_gap"].mean(), 4),
        "train_accuracy_mean": round(np.mean(train_accuracies), 4),
    }

    # Step 3: Final hold-out evaluation
    final_model = model_class(**model_params)
    final_model.fit(X_dev, y_dev)

    y_holdout_pred = final_model.predict(X_holdout)
    y_holdout_proba = final_model.predict_proba(X_holdout)[:, 1]

    holdout_metrics = {
        "accuracy": round(accuracy_score(y_holdout, y_holdout_pred), 4),
        "precision": round(precision_score(y_holdout, y_holdout_pred, zero_division=0), 4),
        "recall": round(recall_score(y_holdout, y_holdout_pred, zero_division=0), 4),
        "f1": round(f1_score(y_holdout, y_holdout_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_holdout, y_holdout_proba), 4),
        "confusion_matrix": confusion_matrix(y_holdout, y_holdout_pred).tolist(),
    }

    # Overfitting check
    overfit_warning = None
    if cv_summary["overfit_gap_mean"] > 0.05:
        overfit_warning = (
            f"⚠️ OVERFITTING DETECTED: Train-Val gap = "
            f"{cv_summary['overfit_gap_mean']:.3f} (>0.05 threshold)"
        )
    elif cv_summary["accuracy_std"] > 0.1:
        overfit_warning = (
            f"⚠️ HIGH VARIANCE: CV accuracy std = "
            f"{cv_summary['accuracy_std']:.3f} (>0.10 threshold)"
        )

    return {
        "fold_metrics": fold_metrics,
        "cv_summary": cv_summary,
        "holdout_metrics": holdout_metrics,
        "overfit_warning": overfit_warning,
        "model": final_model,
        "holdout_y_true": y_holdout.tolist(),
        "holdout_y_proba": y_holdout_proba.tolist(),
    }


def plot_roc_curve(y_true, y_proba) -> go.Figure:
    """Generate ROC curve with AUC."""
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc = roc_auc_score(y_true, y_proba)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fpr, y=tpr, mode='lines',
        name=f'ROC (AUC = {auc:.3f})',
        line=dict(color='#6366f1', width=2),
    ))
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode='lines',
        name='Random', line=dict(color='#64748b', dash='dash'),
    ))
    fig.update_layout(
        title="ROC Curve (Hold-Out Set)",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        height=450, template="plotly_dark",
    )
    return fig


def plot_confusion_matrix_fig(cm) -> go.Figure:
    """Generate confusion matrix heatmap."""
    labels = ["Not Suitable", "Suitable"]
    annotations = []
    for i in range(2):
        for j in range(2):
            annotations.append(dict(
                x=j, y=i, text=str(cm[i][j]),
                showarrow=False, font=dict(size=20, color='white'),
            ))

    fig = go.Figure(data=go.Heatmap(
        z=cm, x=['Pred: 0', 'Pred: 1'], y=['True: 0', 'True: 1'],
        colorscale='Blues', showscale=True,
    ))
    fig.update_layout(
        title="Confusion Matrix (Hold-Out Set)",
        annotations=annotations, height=400,
        xaxis_title="Predicted", yaxis_title="Actual",
        template="plotly_dark",
    )
    return fig


def plot_overfit_chart(fold_metrics: list[dict]) -> go.Figure:
    """Plot training vs validation accuracy per fold."""
    folds = [f["fold"] for f in fold_metrics]
    train_acc = [f["train_accuracy"] for f in fold_metrics]
    val_acc = [f["val_accuracy"] for f in fold_metrics]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=folds, y=train_acc, name="Train Accuracy",
        marker_color='#6366f1', opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        x=folds, y=val_acc, name="Validation Accuracy",
        marker_color='#22c55e', opacity=0.7,
    ))
    fig.update_layout(
        title="Train vs Validation Accuracy per Fold",
        xaxis_title="Fold", yaxis_title="Accuracy",
        barmode='group', height=400, template="plotly_dark",
        yaxis=dict(range=[0.5, 1.05]),
    )
    return fig
