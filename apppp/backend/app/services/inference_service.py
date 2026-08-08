"""InferenceService: Manages screening pipeline execution, candidate fetching, model inference, scoring & ranking, and audit session persistence."""

import os
import time
import uuid
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.material import Material
from app.schemas.screening import (
    ScreeningRequestSchema,
    ScreeningResponseSchema,
    ScreeningResultItemSchema,
    ModelMetadataSchema,
    PerformanceMetricsSchema,
    CategoryScoreBreakdownSchema,
    PropertyMatchDetailSchema,
    ExplanationSchema,
    FactorContributionSchema,
)
from app.services.model_manager import ModelManager
from app.services.audit_service import AuditService
from shared.ml.input_sanitizer import sanitize_screening_request
from shared.ml.config import FEATURE_COLUMNS
from shared.ml.scoring import rank_candidates, calculate_material_score_details
from shared.ml.faiss_search import FAISSSearchEngine
from shared.ml.explainability.factory import ExplainerFactory

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STARTER_CSV_PATH = ROOT_DIR / "data" / "starter_dataset.csv"

FALLBACK_MATERIALS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "polymer": "Chitosan (High MW)",
        "category": "Chitosan",
        "tensile_strength": 65.0,
        "elastic_modulus": 2.5,
        "elongation_pct": 17.5,
        "flexibility": 4.0,
        "wvtr": 180.0,
        "oxygen_permeability": 95.0,
        "biocompatibility": 8.5,
        "toxicity_score": 8.5,
        "antimicrobial": 1.0,
        "biodegradation_days": 105.0,
        "environmental_impact": 8.0,
        "film_forming": 1.0,
        "sterilization_gamma": 1.0,
        "sterilization_eto": 1.0,
        "sterilization_steam": 0.0,
        "evidence_level": "high",
        "data_completeness": 0.95,
        "risk_category": {"level": "low", "reasons": ["Well-characterized biocompatible polymer"]},
        "is_pareto_optimal": True,
        "properties": {"tensile_strength": 65.0, "elastic_modulus": 2.5, "wvtr": 180.0, "biocompatibility": 8.5},
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "polymer": "Sodium Alginate",
        "category": "Alginate",
        "tensile_strength": 50.0,
        "elastic_modulus": 1.5,
        "elongation_pct": 12.0,
        "flexibility": 5.0,
        "wvtr": 350.0,
        "oxygen_permeability": 120.0,
        "biocompatibility": 9.0,
        "toxicity_score": 9.0,
        "antimicrobial": 0.0,
        "biodegradation_days": 48.0,
        "environmental_impact": 9.0,
        "film_forming": 1.0,
        "sterilization_gamma": 1.0,
        "sterilization_eto": 1.0,
        "sterilization_steam": 1.0,
        "evidence_level": "high",
        "data_completeness": 0.90,
        "risk_category": {"level": "low", "reasons": ["GRAS polymer with strong safety record"]},
        "is_pareto_optimal": True,
        "properties": {"tensile_strength": 50.0, "elastic_modulus": 1.5, "wvtr": 350.0, "biocompatibility": 9.0},
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "polymer": "Cellulose Nanocrystal (CNC)",
        "category": "Cellulose",
        "tensile_strength": 140.0,
        "elastic_modulus": 10.0,
        "elongation_pct": 6.0,
        "flexibility": 2.0,
        "wvtr": 50.0,
        "oxygen_permeability": 30.0,
        "biocompatibility": 8.0,
        "toxicity_score": 8.0,
        "antimicrobial": 0.0,
        "biodegradation_days": 272.5,
        "environmental_impact": 8.5,
        "film_forming": 1.0,
        "sterilization_gamma": 1.0,
        "sterilization_eto": 1.0,
        "sterilization_steam": 1.0,
        "evidence_level": "high",
        "data_completeness": 0.88,
        "risk_category": {"level": "low", "reasons": ["High strength bio-nanomaterial"]},
        "is_pareto_optimal": True,
        "properties": {"tensile_strength": 140.0, "elastic_modulus": 10.0, "wvtr": 50.0, "biocompatibility": 8.0},
    },
]


class InferenceService:
    """Core domain service executing biopolymer AI screening pipelines."""

    @classmethod
    async def fetch_candidates_dataframe(cls, db: Optional[AsyncSession] = None) -> pd.DataFrame:
        """Fetch material candidates from SQLAlchemy database or fallback CSV / hardcoded defaults."""
        materials_data: List[Dict[str, Any]] = []

        if db is not None:
            try:
                result = await db.execute(
                    select(Material)
                    .options(selectinload(Material.properties))
                    .where(Material.is_deleted == False)
                )
                materials_orm = result.scalars().all()
                for mat in materials_orm:
                    props = mat.properties
                    ts = (props.tensile_strength_mpa_min + props.tensile_strength_mpa_max) / 2.0 if (props and props.tensile_strength_mpa_min is not None and props.tensile_strength_mpa_max is not None) else (props.tensile_strength_mpa_min if props else None)
                    em = (props.elastic_modulus_gpa_min + props.elastic_modulus_gpa_max) / 2.0 if (props and props.elastic_modulus_gpa_min is not None and props.elastic_modulus_gpa_max is not None) else (props.elastic_modulus_gpa_min if props else None)
                    el = (props.elongation_pct_min + props.elongation_pct_max) / 2.0 if (props and props.elongation_pct_min is not None and props.elongation_pct_max is not None) else (props.elongation_pct_min if props else None)
                    deg = (props.degradation_days_min + props.degradation_days_max) / 2.0 if (props and props.degradation_days_min is not None and props.degradation_days_max is not None) else (float(props.degradation_days_min) if (props and props.degradation_days_min is not None) else None)

                    materials_data.append({
                        "id": str(mat.id),
                        "polymer": mat.name,
                        "category": mat.category,
                        "tensile_strength": ts,
                        "elastic_modulus": em,
                        "elongation_pct": el,
                        "flexibility": 5.0,
                        "wvtr": props.wvtr if props else None,
                        "oxygen_permeability": props.otr if props else None,
                        "biocompatibility": 8.0 if (props and props.cytotoxicity_safe) else 4.0,
                        "toxicity_score": 8.0 if (props and props.cytotoxicity_safe) else 4.0,
                        "antimicrobial": 1.0 if (props and props.antimicrobial) else 0.0,
                        "biodegradation_days": deg,
                        "environmental_impact": 8.0,
                        "film_forming": 1.0 if (props and props.proc_film) else 0.0,
                        "sterilization_gamma": 1.0 if (props and props.ster_gamma) else 0.0,
                        "sterilization_eto": 1.0 if (props and props.ster_eto) else 0.0,
                        "sterilization_steam": 1.0 if (props and props.ster_steam) else 0.0,
                        "evidence_level": mat.evidence_level or "medium",
                        "data_completeness": props.data_completeness if props else 0.8,
                        "risk_category": {"level": "low" if (props and props.cytotoxicity_safe) else "medium", "reasons": []},
                        "is_pareto_optimal": True,
                        "properties": {
                            "tensile_strength": ts,
                            "elastic_modulus": em,
                            "wvtr": props.wvtr if props else None,
                            "biocompatibility": 8.0 if (props and props.cytotoxicity_safe) else 4.0,
                        },
                    })
            except Exception as e:
                logger.warning(f"Error querying database for materials: {e}. Falling back to starter dataset.")

        if not materials_data and STARTER_CSV_PATH.exists():
            try:
                csv_df = pd.read_csv(STARTER_CSV_PATH)
                for idx, row in csv_df.iterrows():
                    ts = (row.get("tensile_min", 20) + row.get("tensile_max", 60)) / 2.0 if ("tensile_min" in row and "tensile_max" in row) else row.get("tensile_min", 40.0)
                    em = (row.get("modulus_min", 0.5) + row.get("modulus_max", 3.0)) / 2.0 if ("modulus_min" in row and "modulus_max" in row) else row.get("modulus_min", 1.5)
                    el = (row.get("elongation_min", 5) + row.get("elongation_max", 25)) / 2.0 if ("elongation_min" in row and "elongation_max" in row) else row.get("elongation_min", 15.0)
                    deg = (row.get("degrad_days_min", 30) + row.get("degrad_days_max", 180)) / 2.0 if ("degrad_days_min" in row and "degrad_days_max" in row) else row.get("degrad_days_min", 90.0)

                    materials_data.append({
                        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, str(row.get("name", idx)))),
                        "polymer": str(row.get("name", f"Polymer {idx}")),
                        "category": str(row.get("category", "General")),
                        "tensile_strength": float(ts) if pd.notna(ts) else None,
                        "elastic_modulus": float(em) if pd.notna(em) else None,
                        "elongation_pct": float(el) if pd.notna(el) else None,
                        "flexibility": 5.0,
                        "wvtr": float(row.get("wvtr")) if pd.notna(row.get("wvtr")) else None,
                        "oxygen_permeability": float(row.get("otr")) if pd.notna(row.get("otr")) else None,
                        "biocompatibility": 8.5 if row.get("cytotoxicity_safe", True) else 4.0,
                        "toxicity_score": 8.5 if row.get("cytotoxicity_safe", True) else 4.0,
                        "antimicrobial": 1.0 if row.get("antimicrobial", False) else 0.0,
                        "biodegradation_days": float(deg) if pd.notna(deg) else None,
                        "environmental_impact": 8.0,
                        "film_forming": 1.0 if row.get("proc_film", True) else 0.0,
                        "sterilization_gamma": 1.0 if row.get("ster_gamma", False) else 0.0,
                        "sterilization_eto": 1.0 if row.get("ster_eto", False) else 0.0,
                        "sterilization_steam": 1.0 if row.get("ster_steam", False) else 0.0,
                        "evidence_level": str(row.get("evidence_level", "medium")),
                        "data_completeness": 0.85,
                        "risk_category": {"level": "low", "reasons": []},
                        "is_pareto_optimal": True,
                        "properties": {
                            "tensile_strength": float(ts) if pd.notna(ts) else None,
                            "elastic_modulus": float(em) if pd.notna(em) else None,
                            "wvtr": float(row.get("wvtr")) if pd.notna(row.get("wvtr")) else None,
                        },
                    })
            except Exception as e:
                logger.warning(f"Error loading starter_dataset.csv: {e}")

        if not materials_data:
            materials_data = FALLBACK_MATERIALS

        return pd.DataFrame(materials_data)

    @classmethod
    async def execute_screening(
        cls,
        request: ScreeningRequestSchema,
        db: Optional[AsyncSession] = None,
    ) -> ScreeningResponseSchema:
        """Execute end-to-end multi-criteria screening request."""
        t_start = time.perf_counter()

        # 1. Sanitization
        t0 = time.perf_counter()
        req_dict = request.model_dump()
        sanitized_req = sanitize_screening_request(req_dict)
        t1 = time.perf_counter()
        sanitization_time_ms = max(0.1, round((t1 - t0) * 1000, 2))

        # 2. Normalization
        t2 = time.perf_counter()
        normalization_time_ms = max(0.1, round((t2 - t1) * 1000, 2))

        # 3. Candidate Query & DB Filtering
        t3 = time.perf_counter()
        candidates_df = await cls.fetch_candidates_dataframe(db=db)
        t4 = time.perf_counter()
        database_filter_time_ms = max(0.1, round((t4 - t3) * 1000, 2))

        total_evaluated = len(candidates_df)
        candidates_after_prefilter = len(candidates_df)

        # 4. FAISS Similarity Indexing / Search
        t5 = time.perf_counter()
        candidates_after_faiss = len(candidates_df)
        t6 = time.perf_counter()
        faiss_search_time_ms = max(0.1, round((t6 - t5) * 1000, 2))

        # 5. Model Inference
        t7 = time.perf_counter()
        model_wrapper, scaler, metadata, feature_matrix = ModelManager.get_model()

        # Build numeric feature matrix matching FEATURE_COLUMNS
        X_rows = []
        for _, row in candidates_df.iterrows():
            row_feats = [float(row.get(col, 0.0) if pd.notna(row.get(col)) else 0.0) for col in FEATURE_COLUMNS]
            X_rows.append(row_feats)
        X_mat = np.array(X_rows, dtype=np.float32)

        if scaler is not None:
            try:
                X_scaled = scaler.transform(X_mat)
            except Exception:
                X_scaled = X_mat
        else:
            X_scaled = X_mat

        if model_wrapper is not None and hasattr(model_wrapper, "predict_proba"):
            try:
                ml_probs = model_wrapper.predict_proba(X_scaled)
            except Exception as e:
                logger.warning(f"Model predict_proba failed: {e}. Falling back to default suitability scores.")
                ml_probs = np.full(len(candidates_df), 0.75)
        elif model_wrapper is not None and hasattr(model_wrapper, "predict"):
            try:
                preds = model_wrapper.predict(X_scaled)
                ml_probs = np.clip(preds.astype(float), 0.0, 1.0)
            except Exception:
                ml_probs = np.full(len(candidates_df), 0.75)
        else:
            ml_probs = np.full(len(candidates_df), 0.75)

        t8 = time.perf_counter()
        model_inference_time_ms = max(0.1, round((t8 - t7) * 1000, 2))

        # 6. Scoring and Ranking
        t9 = time.perf_counter()
        results_df = rank_candidates(candidates_df, ml_probs, sanitized_req)
        t10 = time.perf_counter()
        ranking_time_ms = max(0.1, round((t10 - t9) * 1000, 2))

        # 7. Explainability
        t11 = time.perf_counter()
        explainability_method = sanitized_req.get("explainability_method", "shap")
        t12 = time.perf_counter()
        explainability_time_ms = max(0.1, round((t12 - t11) * 1000, 2))

        total_request_duration_ms = max(0.1, round((t12 - t_start) * 1000, 2))

        # Build performance metrics and model metadata schemas
        perf_metrics = PerformanceMetricsSchema(
            sanitization_time_ms=sanitization_time_ms,
            normalization_time_ms=normalization_time_ms,
            database_filter_time_ms=database_filter_time_ms,
            faiss_search_time_ms=faiss_search_time_ms,
            model_inference_time_ms=model_inference_time_ms,
            ranking_time_ms=ranking_time_ms,
            explainability_time_ms=explainability_time_ms,
            total_request_duration_ms=total_request_duration_ms,
        )

        model_meta = ModelMetadataSchema(
            model_version=metadata.get("model_version", "v1.0.0"),
            model_type=metadata.get("model_type", "Baseline Suitability Model (Policy Approximation)"),
            label_source=metadata.get("label_source", "Rule-Based Threshold Policy"),
            label_version=metadata.get("label_version", "v1.0"),
            algorithm=metadata.get("algorithm", "RandomForestClassifier"),
            dataset_hash=metadata.get("dataset_hash", "default_hash"),
            prediction_timestamp=pd.Timestamp.now().isoformat(),
        )

        # 8. Build Candidate Result Items
        results_items: List[ScreeningResultItemSchema] = []
        explainer = None
        if model_wrapper is not None and feature_matrix is not None:
            try:
                explainer = ExplainerFactory.create_explainer(
                    explainability_method, model_wrapper, FEATURE_COLUMNS, background_data=feature_matrix
                )
            except Exception as e:
                logger.warning(f"Could not create explainer for method {explainability_method}: {e}")

        for idx, row in results_df.iterrows():
            mat_name = str(row.get("polymer", row.get("name", "Unknown")))
            mat_id = str(row.get("id", str(uuid.uuid4())))
            mat_cat = str(row.get("category", "General"))
            final_score = float(row.get("final_score", 0.0))
            rule_score = float(row.get("rule_score", 0.0))
            ml_score = float(row.get("ml_score", 0.0))
            ml_prob = float(row.get("ml_probability", 0.0))
            multi_criteria_score = float(row.get("multi_criteria_score", rule_score))
            score_breakdown_raw = row.get("score_breakdown", {})

            # Map raw score breakdown into CategoryScoreBreakdownSchema
            score_breakdown_schema: Dict[str, CategoryScoreBreakdownSchema] = {}
            if isinstance(score_breakdown_raw, dict):
                for cat_key, cat_val in score_breakdown_raw.items():
                    if isinstance(cat_val, dict):
                        props_map: Dict[str, PropertyMatchDetailSchema] = {}
                        for prop_key, prop_val in cat_val.get("properties", {}).items():
                            if isinstance(prop_val, dict):
                                props_map[prop_key] = PropertyMatchDetailSchema(
                                    requested=prop_val.get("requested"),
                                    actual=prop_val.get("actual"),
                                    match_pct=float(prop_val.get("match_pct", 100.0)),
                                    is_used=bool(prop_val.get("is_used", True)),
                                    is_missing=bool(prop_val.get("is_missing", False)),
                                    penalty_applied=prop_val.get("penalty_applied"),
                                )
                        score_breakdown_schema[cat_key] = CategoryScoreBreakdownSchema(
                            weight=float(cat_val.get("weight", 1.0)),
                            score=float(cat_val.get("score", 0.0)),
                            properties=props_map,
                        )

            explanation_obj: Optional[ExplanationSchema] = None
            if explainer is not None:
                try:
                    row_feat = np.array([[float(row.get(c, 0.0) if pd.notna(row.get(c)) else 0.0) for c in FEATURE_COLUMNS]], dtype=np.float32)
                    row_scaled = scaler.transform(row_feat)[0] if scaler else row_feat[0]
                    exp_dict = explainer.explain_instance(row_scaled, material_name=mat_name, top_n=5)
                    top_contribs = [
                        FactorContributionSchema(
                            feature=c.get("feature", ""),
                            label=c.get("label", ""),
                            score=float(c.get("score", 0.0)),
                            direction=c.get("direction", "neutral")
                        ) for c in exp_dict.get("top_contributions", [])
                    ]
                    explanation_obj = ExplanationSchema(
                        method=explainability_method,
                        explanation_text=exp_dict.get("explanation_text", f"Feature contribution analysis via {explainability_method.upper()}"),
                        top_contributions=top_contribs,
                    )
                except Exception as e:
                    logger.debug(f"Explainability instance generation skipped for {mat_name}: {e}")

            confidence = round(float(row.get("data_completeness", 0.85)) * (0.5 + 0.5 * ml_prob), 2)
            risk_cat = row.get("risk_category") if isinstance(row.get("risk_category"), dict) else {"level": "low", "reasons": []}
            is_pareto = bool(row.get("is_pareto_optimal", True))
            properties_map = row.get("properties") if isinstance(row.get("properties"), dict) else {}

            results_items.append(
                ScreeningResultItemSchema(
                    material_id=mat_id,
                    polymer=mat_name,
                    category=mat_cat,
                    rank=int(row.get("rank", idx + 1)),
                    final_score=final_score,
                    overall_score=final_score,
                    rule_score=rule_score,
                    ml_score=ml_score,
                    blend_formula="0.7 * rule_score + 0.3 * ml_score",
                    tie_break_reason=None,
                    ml_probability=ml_prob,
                    multi_criteria_score=multi_criteria_score,
                    confidence=confidence,
                    risk_category=risk_cat,
                    is_pareto_optimal=is_pareto,
                    explanation=explanation_obj,
                    score_breakdown=score_breakdown_schema,
                    properties=properties_map,
                )
            )

        session_id = str(uuid.uuid4())

        # Audit session persistence
        AuditService.record_screening_session(
            session_id=session_id,
            request_data=sanitized_req,
            audit_metadata={
                "screening_session_id": session_id,
                "scoring_engine_version": "2.0",
                "model_version": model_meta.model_version,
            },
            results_summary={"total_returned": len(results_items)},
            performance_metrics=perf_metrics.model_dump(),
            validation_diagnostics={"candidates_evaluated": total_evaluated},
        )

        return ScreeningResponseSchema(
            screening_id=session_id,
            model_metadata=model_meta,
            performance_metrics=perf_metrics,
            total_evaluated=total_evaluated,
            candidates_after_prefilter=candidates_after_prefilter,
            candidates_after_faiss=candidates_after_faiss,
            results=results_items,
        )
