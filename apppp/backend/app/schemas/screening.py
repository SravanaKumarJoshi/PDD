"""Pydantic schemas for screening API requests, responses, performance metrics, and model metadata."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ScreeningRequestSchema(BaseModel):
    tensile_strength: Optional[float] = Field(None, ge=0.0, description="Target tensile strength in MPa")
    elastic_modulus: Optional[float] = Field(None, ge=0.0, description="Target elastic modulus in GPa")
    elongation_pct: Optional[float] = Field(None, ge=0.0, description="Target elongation %")
    flexibility: Optional[float] = Field(None, ge=1.0, le=10.0, description="Flexibility scale 1-10")
    wvtr: Optional[float] = Field(None, ge=0.0, description="Max WVTR barrier limit")
    oxygen_permeability: Optional[float] = Field(None, ge=0.0, description="Max O2 permeability")
    min_biocompatibility: Optional[float] = Field(None, ge=0.0, le=10.0, description="Minimum biocompatibility rating 0-10")
    target_biodegradation_days: Optional[float] = Field(None, ge=1.0, le=1000.0, description="Target biodegradation time in days")
    sterilization_gamma: bool = Field(False, description="Require gamma sterilization support")
    sterilization_eto: bool = Field(False, description="Require EtO sterilization support")
    sterilization_steam: bool = Field(False, description="Require steam sterilization support")
    explainability_method: Optional[str] = Field("shap", description="Explainability strategy: shap or lime")

    # Optional criterion weight overrides (0.0 to 3.0)
    weight_mechanical: float = Field(1.0, ge=0.0, le=3.0)
    weight_barrier: float = Field(1.0, ge=0.0, le=3.0)
    weight_biological: float = Field(1.2, ge=0.0, le=3.0)
    weight_degradation: float = Field(1.0, ge=0.0, le=3.0)
    weight_processing: float = Field(0.8, ge=0.0, le=3.0)
    weight_sterilization: float = Field(1.0, ge=0.0, le=3.0)


class PropertyMatchDetailSchema(BaseModel):
    requested: Optional[Any] = None
    actual: Optional[Any] = None
    match_pct: float = Field(..., ge=0.0, le=100.0)
    is_used: bool = True
    is_missing: bool = False
    penalty_applied: Optional[str] = None


class CategoryScoreBreakdownSchema(BaseModel):
    weight: float = Field(..., ge=0.0)
    score: float = Field(..., ge=0.0, le=100.0)
    properties: Dict[str, PropertyMatchDetailSchema] = {}


class FactorContributionSchema(BaseModel):
    feature: str
    label: str
    score: float
    direction: str


class ExplanationSchema(BaseModel):
    method: str
    explanation_text: str
    top_contributions: List[FactorContributionSchema]


class RiskCategorySchema(BaseModel):
    level: Optional[str] = "low"
    label: str = "Low Confidence — verify experimentally"
    color: str = "red"
    reasons: List[str] = Field(default_factory=list)


class ScreeningResultItemSchema(BaseModel):
    material_id: str
    polymer: str
    category: str
    rank: int = 1
    final_score: float
    overall_score: float
    rule_score: float
    ml_score: float
    blend_formula: str = "0.7 * rule_score + 0.3 * ml_score"
    tie_break_reason: Optional[str] = None
    ml_probability: float
    multi_criteria_score: float
    confidence: float
    risk_category: RiskCategorySchema
    is_pareto_optimal: bool
    explanation: Optional[ExplanationSchema] = None
    score_breakdown: Dict[str, CategoryScoreBreakdownSchema] = {}
    properties: Dict[str, Any] = {}



class ModelMetadataSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_version: str
    model_type: Optional[str] = "Baseline Suitability Model (Policy Approximation)"
    label_source: Optional[str] = "Rule-Based Threshold Policy"
    label_version: Optional[str] = "v1.0"
    algorithm: str
    dataset_hash: str
    prediction_timestamp: str


class PerformanceMetricsSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    sanitization_time_ms: float
    normalization_time_ms: float
    database_filter_time_ms: float
    faiss_search_time_ms: float
    model_inference_time_ms: float
    ranking_time_ms: float
    explainability_time_ms: float
    total_request_duration_ms: float


class ScreeningResponseSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    screening_id: str
    model_metadata: ModelMetadataSchema
    performance_metrics: PerformanceMetricsSchema
    total_evaluated: int
    candidates_after_prefilter: int
    candidates_after_faiss: int
    results: List[ScreeningResultItemSchema]
