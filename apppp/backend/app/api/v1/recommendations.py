"""Recommendations API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.material import Material
from app.schemas.recommendation import (
    RequirementInput,
    RecommendationResponse,
)
from app.scoring.engine import score_and_rank

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    requirements: RequirementInput,
    db: AsyncSession = Depends(get_db),
):
    """Submit requirements and get ranked biopolymer recommendations."""
    # Fetch all active materials with properties
    result = await db.execute(
        select(Material)
        .options(selectinload(Material.properties))
        .where(Material.is_deleted == False)  # noqa: E712
    )
    materials_orm = result.scalars().all()

    # Convert to dicts for scoring engine
    materials_data = []
    for mat in materials_orm:
        mat_dict = {
            "id": str(mat.id),
            "name": mat.name,
            "category": mat.category,
            "evidence_level": mat.evidence_level,
        }
        if mat.properties:
            props = mat.properties
            mat_dict["properties"] = {
                "tensile_strength_mpa_min": props.tensile_strength_mpa_min,
                "tensile_strength_mpa_max": props.tensile_strength_mpa_max,
                "elastic_modulus_gpa_min": props.elastic_modulus_gpa_min,
                "elastic_modulus_gpa_max": props.elastic_modulus_gpa_max,
                "elongation_pct_min": props.elongation_pct_min,
                "elongation_pct_max": props.elongation_pct_max,
                "puncture_resistance_n": props.puncture_resistance_n,
                "wvtr": props.wvtr,
                "otr": props.otr,
                "water_solubility": props.water_solubility,
                "swelling_ratio": props.swelling_ratio,
                "degradation_days_min": props.degradation_days_min,
                "degradation_days_max": props.degradation_days_max,
                "enzymatic_degradability": props.enzymatic_degradability,
                "hydrolytic_stability": props.hydrolytic_stability,
                "cytotoxicity_safe": props.cytotoxicity_safe,
                "hemocompatible": props.hemocompatible,
                "antimicrobial": props.antimicrobial,
                "endotoxin_concern": props.endotoxin_concern,
                "ster_gamma": props.ster_gamma,
                "ster_eto": props.ster_eto,
                "ster_steam": props.ster_steam,
                "ster_uv": props.ster_uv,
                "ster_autoclave": props.ster_autoclave,
                "proc_film": props.proc_film,
                "proc_casting": props.proc_casting,
                "proc_extrusion": props.proc_extrusion,
                "proc_coating": props.proc_coating,
                "proc_melt": props.proc_melt,
                "solvent_compatible": props.solvent_compatible,
                "cost_band": props.cost_band,
                "availability_band": props.availability_band,
                "data_completeness": props.data_completeness,
            }
        else:
            mat_dict["properties"] = {}

        materials_data.append(mat_dict)

    return score_and_rank(requirements, materials_data)
