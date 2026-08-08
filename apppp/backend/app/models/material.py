"""Material and MaterialProperty models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Text, text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import JSON

from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_level: Mapped[str] = mapped_column(
        String(10), default="low", server_default="low"
    )
    # `REFERENCES` is a reserved MySQL keyword.  Keep the public Python/API
    # attribute but use a safe physical column name so CREATE TABLE succeeds.
    references: Mapped[dict] = mapped_column("material_references", JSON, default=list)
    ext_properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"), onupdate=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))

    properties: Mapped["MaterialProperty"] = relationship(
        back_populates="material", uselist=False, cascade="all, delete-orphan"
    )


class MaterialProperty(Base):
    __tablename__ = "material_properties"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), unique=True
    )

    # Mechanical
    tensile_strength_mpa_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    tensile_strength_mpa_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    elastic_modulus_gpa_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    elastic_modulus_gpa_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    elongation_pct_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    elongation_pct_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    puncture_resistance_n: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Barrier
    wvtr: Mapped[float | None] = mapped_column(Float, nullable=True)
    otr: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Solubility
    water_solubility: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    swelling_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Degradation
    degradation_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    degradation_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enzymatic_degradability: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hydrolytic_stability: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Biological
    cytotoxicity_safe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hemocompatible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    antimicrobial: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    endotoxin_concern: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Sterilization
    ster_gamma: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    ster_eto: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    ster_steam: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    ster_uv: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    ster_autoclave: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))

    # Processing
    proc_film: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    proc_casting: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    proc_extrusion: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    proc_coating: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    proc_melt: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    solvent_compatible: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cost & Availability
    cost_band: Mapped[str | None] = mapped_column(String(10), nullable=True)
    availability_band: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Meta
    data_completeness: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"), onupdate=lambda: datetime.now(timezone.utc)
    )

    material: Mapped["Material"] = relationship(back_populates="properties")
