"""Pydantic schemas for Materials API."""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class MaterialPropertySchema(BaseModel):
    # Mechanical
    tensile_strength_mpa_min: float | None = None
    tensile_strength_mpa_max: float | None = None
    elastic_modulus_gpa_min: float | None = None
    elastic_modulus_gpa_max: float | None = None
    elongation_pct_min: float | None = None
    elongation_pct_max: float | None = None
    puncture_resistance_n: float | None = None

    # Barrier
    wvtr: float | None = None
    otr: float | None = None

    # Solubility
    water_solubility: bool | None = None
    swelling_ratio: float | None = None

    # Degradation
    # Note: stored as FLOAT in MySQL (biodegradation_days may contain fractional
    # values such as 4.23).  Using float here prevents Pydantic validation errors
    # when the DB column contains non-integer values.
    degradation_days_min: float | None = None
    degradation_days_max: float | None = None
    enzymatic_degradability: bool | None = None
    hydrolytic_stability: str | None = None

    # Biological
    cytotoxicity_safe: bool | None = None
    hemocompatible: bool | None = None
    antimicrobial: bool | None = None
    endotoxin_concern: str | None = None

    # Sterilization
    ster_gamma: bool = False
    ster_eto: bool = False
    ster_steam: bool = False
    ster_uv: bool = False
    ster_autoclave: bool = False

    # Processing
    proc_film: bool = False
    proc_casting: bool = False
    proc_extrusion: bool = False
    proc_coating: bool = False
    proc_melt: bool = False
    solvent_compatible: str | None = None

    # Cost
    cost_band: str | None = None
    availability_band: str | None = None

    # Meta
    data_completeness: float = 0.0

    model_config = {"from_attributes": True}


class MaterialResponse(BaseModel):
    # MySQL primary key serialized as a string; this is the synchronization key.
    id: str
    name: str
    category: str
    source: str | None = None
    notes: str | None = None
    evidence_level: str = "low"
    references: list = Field(default_factory=list)
    ext_properties: dict = Field(default_factory=dict)
    properties: MaterialPropertySchema | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    source: str | None = None
    notes: str | None = None
    evidence_level: str = "low"
    references: list = Field(default_factory=list)
    ext_properties: dict = Field(default_factory=dict)
    properties: MaterialPropertySchema | None = None


class MaterialUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    source: str | None = None
    notes: str | None = None
    evidence_level: str | None = None
    references: list | None = None
    ext_properties: dict | None = None
    properties: MaterialPropertySchema | None = None


class MaterialSyncResponse(BaseModel):
    materials: list[MaterialResponse]
    server_timestamp: datetime
