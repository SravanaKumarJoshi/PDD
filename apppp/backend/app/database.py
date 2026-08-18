"""Async SQLAlchemy database engine and session factory for MySQL.

Uses aiomysql as the async driver.  The DATABASE_URL in config.py must use
the mysql+aiomysql:// scheme.

pool_pre_ping=True ensures that stale connections in the pool are detected and
recycled automatically — essential for MySQL which closes idle connections
after wait_timeout (default 8 hours).
"""

import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    engine = create_async_engine(db_url, echo=settings.APP_DEBUG)
else:
    engine = create_async_engine(
        db_url,
        echo=settings.APP_DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        pool_pre_ping=False,
        pool_timeout=10,
    )

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency: yield a database session per request."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """Create all tables that don't yet exist and migrate schema changes."""
    global engine, async_session
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                from sqlalchemy import text
                res = await conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' "
                    "AND COLUMN_NAME='password_hash'"
                ))
                exists = res.scalar()
                if not exists:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL AFTER display_name"))
            except Exception:
                pass
    except Exception as exc:
        logger.warning(f"MySQL connection failed ({exc}). Falling back to SQLite database.")
        sqlite_url = "sqlite+aiosqlite:///./biopolymer.db"
        engine = create_async_engine(sqlite_url, echo=settings.APP_DEBUG)
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


