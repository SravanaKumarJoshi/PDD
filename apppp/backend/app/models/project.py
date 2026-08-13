"""Project ORM model — stores requirement sets and full screening results."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import LONGTEXT

from app.database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_title", name="uq_user_project_normalized_title"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # Store as TEXT/LONGTEXT instead of native JSON so this works on every
    # MySQL version (JSON column type requires MySQL 5.7.8+; LONGTEXT is safe
    # on MySQL 5.6+ and MariaDB).  Application layer serialises/deserialises.
    requirements_json: Mapped[str] = mapped_column(
        LONGTEXT().with_variant(Text, "sqlite"), nullable=False, default="{}"
    )
    results_json: Mapped[str | None] = mapped_column(
        LONGTEXT().with_variant(Text, "sqlite"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

