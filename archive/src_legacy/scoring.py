"""
Full 7-step scoring pipeline:
1. User Input → parse & validate
2. Safety Gate → hard reject unsafe materials
3. FAISS Similarity → filter to top-K
4. XGBoost + RF Ensemble → predict suitability
5. NSGA-II on top-N → Pareto-optimal subset
6. SHAP → explain each recommendation
7. Confidence → calibrated probability + risk category
"""
import numpy as np
import pandas as pd
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.data import FEATURE_COLUMNS
from src.safety_gate import run_safety_gate, SafetyResult
from src import faiss_similarity
from src.xgboost_model import predict_suitability as xgb_predict
from src.model import predict_suitability as rf_predict, ensemble_predict
from src.genetic_algorithm import run_nsga2, get_pareto_materials
from src.explainability import compute_shap_values, generate_explanation_text
from src.confidence import (
    compute_confidence_score, get_risk_category,
    compute_prediction_uncertainty,
)
from src.input_validator import validate_user_input
from src.performance import PipelineTimer
from src.monitoring import log_prediction
from src.audit import log_decision_trace


@dataclass
class ScoredMaterial:
    polymer: str
    category: str
    final_score: float
    confidence: float
    risk_category: str
    uncertainty: float
    explanation: str
    is_pareto: bool
    warnings: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    shap_values: Any = None
    similar_score_alternatives: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    ranked_materials: list[ScoredMaterial]
    pareto_front: list[str]
    safety_rejections: list[dict]
    safety_warnings: dict
    pipeline_metadata: dict = field(default_factory=dict)
    input_validation_warnings: list[str] = field(default_factory=list)
    latency_report: dict = field(default_factory=dict)
    request_id: str = ""


def run_full_pipeline(
    df: pd.DataFrame,
    user_requirements: dict,
    xgb_model=None,
    rf_model=None,
    dataset_stats: dict = None,
    top_k_similarity: int = 30,
    top_n_ga: int = 15,
) -> PipelineResult:
    """Execute the full 7-step recommendation pipeline with guardrails."""

    timer = PipelineTimer()
    timer.start_pipeline()
    request_id = str(uuid.uuid4())[:8]
    metadata = {"steps_completed": []}

    # Step 0: Input Validation
    timer.start_stage("input_validation")
    validation = validate_user_input(user_requirements)
    timer.end_stage("input_validation")

    input_warnings = validation.warnings.copy()
    if not validation.is_valid:
        return PipelineResult(
            ranked_materials=[],
            pareto_front=[],
            safety_rejections=[],
            safety_warnings={},
            pipeline_metadata={"errors": validation.errors},
            input_validation_warnings=validation.errors,
            request_id=request_id,
        )

    metadata["total_materials"] = len(df)
    metadata["steps_completed"].append("input_validation")

    # Step 2: Safety Gate
    timer.start_stage("safety_gate")
    safety = run_safety_gate(df, user_requirements)
    approved_df = safety.approved
    timer.end_stage("safety_gate")
    metadata["steps_completed"].append("safety_gate")

    if len(approved_df) == 0:
        return PipelineResult(
            ranked_materials=[],
            pareto_front=[],
            safety_rejections=safety.rejected,
            safety_warnings=safety.warnings,
            pipeline_metadata=metadata,
        )

    # Step 3: FAISS Similarity filtering
    timer.start_stage("faiss_similarity")
    query_features = _build_query_vector(user_requirements)
    faiss_similarity.build_index(approved_df)
    k = min(top_k_similarity, len(approved_df))
    similar_df = faiss_similarity.find_similar_materials(
        approved_df, query_features, k=k,
    )
    timer.end_stage("faiss_similarity")
    metadata["similarity_candidates"] = len(similar_df)
    metadata["steps_completed"].append("faiss_similarity")

    # Step 4: XGBoost + RF Ensemble prediction
    timer.start_stage("ensemble_prediction")
    if xgb_model is not None:
        xgb_proba = xgb_predict(xgb_model, similar_df)
    else:
        xgb_proba = np.full(len(similar_df), 0.5)

    if rf_model is not None:
        rf_proba = rf_predict(rf_model, similar_df)
    else:
        rf_proba = xgb_proba.copy()

    ensemble_proba = ensemble_predict(xgb_proba, rf_proba)
    timer.end_stage("ensemble_prediction")
    metadata["steps_completed"].append("ensemble_prediction")

    # Step 5: NSGA-II on top-N
    timer.start_stage("nsga2_optimization")
    top_n = min(top_n_ga, len(similar_df))
    top_indices = np.argsort(ensemble_proba)[::-1][:top_n]
    ga_candidates = []
    for idx in top_indices:
        row = similar_df.iloc[idx]
        ga_candidates.append(row.to_dict())

    ga_result = run_nsga2(ga_candidates)
    pareto_names = [ga_candidates[i]["polymer"]
                    for i in ga_result["pareto_indices"]]
    timer.end_stage("nsga2_optimization")
    metadata["pareto_count"] = len(pareto_names)
    metadata["steps_completed"].append("nsga2_optimization")

    # Step 6: SHAP explanations
    timer.start_stage("shap_explainability")
    shap_explanations = {}
    shap_vals_array = None
    if xgb_model is not None:
        try:
            X_explain = similar_df[FEATURE_COLUMNS]
            shap_result = compute_shap_values(xgb_model, X_explain)
            vals = shap_result.values
            if vals.ndim == 3:
                vals = vals[:, :, 1]
            shap_vals_array = vals
            for i, (_, row) in enumerate(similar_df.iterrows()):
                shap_explanations[row["polymer"]] = generate_explanation_text(
                    vals[i], FEATURE_COLUMNS, row["polymer"],
                )
        except Exception:
            pass
    timer.end_stage("shap_explainability")
    metadata["steps_completed"].append("shap_explainability")

    # Step 7: Confidence scoring
    timer.start_stage("confidence_scoring")
    uncertainties = np.zeros(len(similar_df))
    if xgb_model is not None:
        try:
            uncertainties = compute_prediction_uncertainty(
                xgb_model, similar_df[FEATURE_COLUMNS],
            )
        except Exception:
            pass
    metadata["steps_completed"].append("confidence_scoring")

    # Build final ranked results
    scored_materials = []
    for i, (_, row) in enumerate(similar_df.iterrows()):
        name = row["polymer"]
        conf = compute_confidence_score(
            ensemble_proba[i],
            row.get("evidence_level", "med"),
            row.get("data_completeness", 1.0),
        )
        risk = get_risk_category(conf)

        scored_materials.append(ScoredMaterial(
            polymer=name,
            category=row.get("category", ""),
            final_score=round(float(ensemble_proba[i]) * 100, 1),
            confidence=conf,
            risk_category=risk["label"],
            uncertainty=round(float(uncertainties[i]), 4),
            explanation=shap_explanations.get(name, ""),
            is_pareto=name in pareto_names,
            warnings=safety.warnings.get(name, []),
            properties={c: row[c] for c in FEATURE_COLUMNS if c in row},
            shap_values=shap_vals_array[i].tolist() if shap_vals_array is not None else None,
        ))

    scored_materials.sort(key=lambda m: m.final_score, reverse=True)

    # Output safety guardrails
    for m in scored_materials:
        if m.confidence < 0.5:
            m.warnings.append(
                "⚠️ Low confidence — experimental validation required"
            )

    # Detect similar-score alternatives
    if len(scored_materials) >= 2:
        top_score = scored_materials[0].final_score
        alts = [
            m.polymer for m in scored_materials[1:5]
            if abs(m.final_score - top_score) < 5.0
        ]
        if alts:
            scored_materials[0].similar_score_alternatives = alts

    timer.end_stage("confidence_scoring")
    metadata["steps_completed"].append("confidence_scoring")

    latency_report = timer.get_report()
    metadata["latency"] = latency_report

    # Log prediction for monitoring
    if scored_materials:
        top = scored_materials[0]
        try:
            log_prediction(
                input_params=user_requirements,
                output_material=top.polymer,
                score=top.final_score,
                confidence=top.confidence,
                risk_category=top.risk_category,
                pipeline_latency_ms=latency_report.get("total_ms", 0),
            )
        except Exception:
            pass

    # Audit trail
    try:
        log_decision_trace(
            request_id=request_id,
            input_params=user_requirements,
            model_version="session",
            safety_rejections=safety.rejected,
            ranked_materials=scored_materials,
            pareto_front=pareto_names,
            pipeline_metadata=metadata,
            latency_report=latency_report,
        )
    except Exception:
        pass

    return PipelineResult(
        ranked_materials=scored_materials,
        pareto_front=pareto_names,
        safety_rejections=safety.rejected,
        safety_warnings=safety.warnings,
        pipeline_metadata=metadata,
        input_validation_warnings=input_warnings,
        latency_report=latency_report,
        request_id=request_id,
    )


def _build_query_vector(requirements: dict) -> dict:
    """Convert user requirements to a feature vector for FAISS query."""
    return {
        "tensile_strength": requirements.get("target_tensile_strength", 50),
        "elastic_modulus": requirements.get("target_elastic_modulus", 2.0),
        "elongation_pct": requirements.get("target_elongation", 20),
        "flexibility": requirements.get("target_flexibility", 7),
        "wvtr": requirements.get("target_wvtr", 300),
        "oxygen_permeability": requirements.get("target_oxygen_permeability", 100),
        "biocompatibility": requirements.get("min_biocompatibility", 7),
        "toxicity_score": 9,
        "antimicrobial": 1 if requirements.get("requires_antimicrobial") else 0,
        "biodegradation_days": (
            requirements.get("biodeg_min", 30) + requirements.get("biodeg_max", 180)
        ) / 2,
        "environmental_impact": 8,
        "film_forming": 1,
        "sterilization_gamma": 1 if requirements.get("sterilization_gamma") else 0,
        "sterilization_eto": 1 if requirements.get("sterilization_eto") else 0,
        "sterilization_steam": 1 if requirements.get("sterilization_steam") else 0,
    }
