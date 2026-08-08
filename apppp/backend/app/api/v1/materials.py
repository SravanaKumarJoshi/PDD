"""MySQL-backed material catalog API (uses configurable table name from config)."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from shared.ml.config import MATERIAL_TABLE_NAME, FEATURE_COLUMNS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/materials", tags=["Materials Catalog"])

@router.get("")
@router.get("/catalog")
async def get_materials(
    category: Optional[str] = Query(None, description="Filter by material category"),
    search: Optional[str] = Query(None, description="Search query string"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=500, description="Limit for pagination"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Fetch paginated, filtered material records from MySQL source of truth."""
    if page is not None:
        skip = (page - 1) * limit

    where_clauses = []
    params = {"skip": skip, "limit": limit}

    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    if search:
        where_clauses.append("(polymer LIKE :search OR category LIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    query = text(f"SELECT * FROM {MATERIAL_TABLE_NAME} {where_sql} LIMIT :limit OFFSET :skip")

    try:
        result = await db.execute(query, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error querying materials from {MATERIAL_TABLE_NAME}: {e}", exc_info=True)
        from scripts.train_pipeline import load_data_from_mysql_or_fallback
        df = load_data_from_mysql_or_fallback()
        if category:
            df = df[df["category"] == category]
        if search:
            df = df[df["polymer"].astype(str).str.contains(search, case=False, na=False)]
        return df.iloc[skip:skip+limit].to_dict(orient="records")

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)) -> List[str]:
    """Get list of distinct material categories."""
    try:
        result = await db.execute(text(f"SELECT DISTINCT category FROM {MATERIAL_TABLE_NAME} WHERE category IS NOT NULL"))
        rows = result.scalars().all()
        return list(rows)
    except Exception:
        return ["Polysaccharide", "Protein", "Synthetic Biopolymer", "Blend"]

@router.get("/properties")
async def get_property_schema() -> Dict[str, Any]:
    """Get feature columns and properties schema."""
    return {
        "features": FEATURE_COLUMNS,
        "total_features": len(FEATURE_COLUMNS),
        "configurable_table": MATERIAL_TABLE_NAME
    }

@router.get("/{material_id}")
@router.get("/details/{material_id}")
async def get_material(
    material_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Fetch single material record by identifier or polymer name."""
    try:
        query = text(f"SELECT * FROM {MATERIAL_TABLE_NAME} WHERE id = :id OR polymer = :id LIMIT 1")
        result = await db.execute(query, {"id": material_id})
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Material '{material_id}' not found.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching material {material_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Material '{material_id}' not found.")
