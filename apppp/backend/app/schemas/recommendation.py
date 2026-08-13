"""Pydantic schemas for Requirements and Recommendations."""

from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field


class MechanicalRequirements(BaseModel):
    tensile_strength_min: float | None = None
    tensile_strength_max: float | None = None
    elastic_modulus_min: float | None = None
    elastic_modulus_max: float | None = None
    elongation_min: float | None = None
    elongation_max: float | None = None
    puncture_resistance_min: float | None = None
    weight: float = Field(default=1.0, ge=0, le=3.0)


class BarrierRequirements(BaseModel):
    wvtr_max: float | None = None
    otr_max: float | None = None
    weight: float = Field(default=1.0, ge=0, le=3.0)


class BiologicalRequirements(BaseModel):
    cytotoxicity_safe_required: bool = False
    hemocompatible_required: bool = False
    antimicrobial_required: bool = False
    low_endotoxin_required: bool = False
    weight: float = Field(default=1.2, ge=0, le=3.0)


class DegradationRequirements(BaseModel):
    degradation_days_min: int | None = None
    degradation_days_max: int | None = None
    enzymatic_required: bool = False
    hydrolytic_stability_min: str | None = None  # low/med/high
    weight: float = Field(default=1.0, ge=0, le=3.0)


class ProcessingRequirements(BaseModel):
    film_required: bool = False
    casting_required: bool = False
    extrusion_required: bool = False
    coating_required: bool = False
    melt_required: bool = False
    solvent_notes: str | None = None
    weight: float = Field(default=0.8, ge=0, le=3.0)


class SterilizationRequirements(BaseModel):
    gamma_required: bool = False
    eto_required: bool = False
    steam_required: bool = False
    uv_required: bool = False
    autoclave_required: bool = False
    weight: float = Field(default=1.0, ge=0, le=3.0)


class SustainabilityRequirements(BaseModel):
    renewable_required: bool = False
    compostable_required: bool = False
    weight: float = Field(default=0.6, ge=0, le=3.0)


class CostRequirements(BaseModel):
    max_cost_band: str | None = None  # low/med/high
    min_availability_band: str | None = None  # low/med/high
    weight: float = Field(default=0.4, ge=0, le=3.0)


class RequirementInput(BaseModel):
    mechanical: MechanicalRequirements = Field(default_factory=MechanicalRequirements)
    barrier: BarrierRequirements = Field(default_factory=BarrierRequirements)
    biological: BiologicalRequirements = Field(default_factory=BiologicalRequirements)
    degradation: DegradationRequirements = Field(default_factory=DegradationRequirements)
    processing: ProcessingRequirements = Field(default_factory=ProcessingRequirements)
    sterilization: SterilizationRequirements = Field(default_factory=SterilizationRequirements)
    sustainability: SustainabilityRequirements = Field(default_factory=SustainabilityRequirements)
    cost: CostRequirements = Field(default_factory=CostRequirements)


class FactorContribution(BaseModel):
    factor: str
    score: float
    description: str


class RecommendationResult(BaseModel):
    material_id: UUID
    material_name: str
    category: str
    score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)
    top_factors: list[FactorContribution]
    concerns: list[FactorContribution]
    unmet_constraints: list[str]
    tradeoffs: list[str]


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationResult]
    scoring_version: str
    total_materials_evaluated: int
    materials_filtered_out: int
