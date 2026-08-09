import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd

_p = Path(__file__).resolve().parent
while _p.parent != _p:
    if (_p / "src").exists():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
    _p = _p.parent

from src.data import load_dataset_from_mysql
from src.genetic_algorithm import run_nsga2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/optimization", tags=["Optimization"])


class ParetoRequestSchema(BaseModel):
    top_n: int = Field(15, ge=5, le=50, description="Top-N candidates to include")
    n_generations: int = Field(50, ge=10, le=200, description="Generations for GA")
    min_biocompatibility: int = Field(6, ge=1, le=10, description="Minimum biocompatibility filter")


@router.post("/pareto")
async def get_pareto_front(payload: ParetoRequestSchema):
    """Run NSGA-II multi-objective optimization for top candidates."""
    try:
        df, stats, error = load_dataset_from_mysql()
        if error:
            raise RuntimeError(error)

        filtered = df[df["biocompatibility"] >= payload.min_biocompatibility].copy()
        if filtered.empty:
            filtered = df.copy()

        filtered = filtered.sort_values("biocompatibility", ascending=False).head(payload.top_n)
        candidates = filtered.to_dict("records")

        if not candidates:
            raise HTTPException(status_code=400, detail="No candidate materials match the filter criteria.")

        result = run_nsga2(candidates, n_generations=payload.n_generations)
        pareto_indices = set(result["pareto_indices"])

        formatted_candidates = []
        for i, c in enumerate(candidates):
            strength = min(c.get("tensile_strength", 0) / 300.0, 1.0)
            biodeg = 1.0 - min(c.get("biodegradation_days", 365) / 730.0, 1.0)
            biocomp = min(c.get("biocompatibility", 0) / 10.0, 1.0)

            formatted_candidates.append({
                "index": i,
                "polymer": c["polymer"],
                "category": c.get("category", ""),
                "tensile_strength": c.get("tensile_strength", 0.0),
                "biodegradation_days": c.get("biodegradation_days", 0),
                "biocompatibility": c.get("biocompatibility", 0),
                "norm_strength": float(strength),
                "norm_biodeg": float(biodeg),
                "norm_biocomp": float(biocomp),
                "is_pareto": i in pareto_indices
            })

        pareto_materials = [c for c in formatted_candidates if c["is_pareto"]]

        return {
            "total_evaluated": len(candidates),
            "pareto_count": len(pareto_materials),
            "candidates": formatted_candidates,
            "pareto_materials": pareto_materials
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NSGA-II optimization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )
