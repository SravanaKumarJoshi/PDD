"""Async SQLAlchemy database engine and session factory for MySQL.

Uses aiomysql as the async driver.  The DATABASE_URL in config.py must use
the mysql+aiomysql:// scheme.

pool_pre_ping=True ensures that stale connections in the pool are detected and
recycled automatically — essential for MySQL which closes idle connections
after wait_timeout (default 8 hours).
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    # MySQL-specific pool settings
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,   # recycle connections every 30 min (< MySQL wait_timeout)
    # SQLAlchemy 2.0.27 + aiomysql 0.2.0 incompatibility: its pre-ping path
    # calls AsyncAdapt_aiomysql_connection.ping() with no reconnect argument.
    # pool_recycle still replaces idle connections before MySQL closes them.
    pool_pre_ping=False,
    pool_timeout=30,
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
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all tables that don't yet exist.

    Called from the app lifespan on startup.  In production, prefer explicit
    SQL migrations (see scripts/migrate.sql); this function is kept as a
    convenience for development and CI.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
