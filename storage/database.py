"""Database connection, engine configuration, and sessionmaker for PostgreSQL 16 + pgvector.

Provides:
- Async engine & sessionmaker for FastAPI asynchronous routes.
- Sync engine & sessionmaker for Celery background tasks and Alembic migrations.
- Base declarative class using SQLAlchemy 2.0 DeclarativeBase.
- get_db() FastAPI dependency generator.
"""

import os
from collections.abc import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DEFAULT_ASYNC_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/socmint"
DEFAULT_SYNC_URL = "postgresql://postgres:postgres@127.0.0.1:5432/socmint"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_ASYNC_URL)
DATABASE_SYNC_URL = os.getenv("DATABASE_SYNC_URL", DEFAULT_SYNC_URL)

# --- Declarative Base ---
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 ORM models."""
    pass


# --- Async Engine & Session (FastAPI) ---
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# --- Sync Engine & Session (Celery Workers & Alembic) ---
sync_engine = create_engine(
    DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# --- FastAPI Dependency ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous database session for FastAPI request lifecycles."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Return a synchronous database session for Celery tasks. Caller must close."""
    return SyncSessionLocal()
