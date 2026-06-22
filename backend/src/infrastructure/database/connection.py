from __future__ import annotations
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_mysql_dsn() -> str | None:
    dsn = os.getenv("MYSQL_DSN")
    if dsn:
        return dsn
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "123456")
    database = os.getenv("MYSQL_DATABASE", "stocks")
    if not all([host, user, password, database]):
        return None
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"


def _init_mysql_engine() -> None:
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return
    dsn = _build_mysql_dsn()
    if not dsn:
        return
    _engine = create_async_engine(
        dsn,
        connect_args={"server_public_key": True},
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    _session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    _init_mysql_engine()
    return _session_factory


def get_mysql_engine() -> AsyncEngine | None:
    _init_mysql_engine()
    return _engine


async def close_mysql_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends session provider."""
    sf = get_session_factory()
    if sf is None:
        raise RuntimeError("MySQL not configured")
    session = sf()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
