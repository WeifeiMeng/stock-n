"""
MySQL 中间件与连接管理。
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.middleware.base import BaseHTTPMiddleware

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_mysql_dsn() -> str | None:
    """
    优先使用 MYSQL_DSN；若未提供，则由分项变量拼接。
    """
    direct_dsn = os.getenv("MYSQL_DSN")
    if direct_dsn:
        return direct_dsn

    host = os.getenv("MYSQL_HOST","localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER","root")
    password = os.getenv("MYSQL_PASSWORD","123456")
    database = os.getenv("MYSQL_DATABASE","stocks")

    if not all([host, user, password, database]):
        return None

    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"


def _init_mysql_engine() -> None:
    """
    初始化全局引擎和 Session 工厂；缺少配置时保持关闭状态。
    """
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return

    dsn = _build_mysql_dsn()
    if not dsn:
        return

    _engine = create_async_engine(
        dsn,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """
    获取 Session 工厂；当未配置 MySQL 时返回 None。
    """
    _init_mysql_engine()
    return _session_factory


def get_mysql_engine() -> AsyncEngine | None:
    """
    获取 MySQL 异步引擎；当未配置 MySQL 时返回 None。
    """
    _init_mysql_engine()
    return _engine


async def close_mysql_engine() -> None:
    """
    应用关闭时释放连接池资源。
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    可用于 FastAPI Depends 的会话提供器。
    """
    session_factory = get_session_factory()
    if session_factory is None:
        raise RuntimeError(
            "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
        )

    session = session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


class MySQLSessionMiddleware(BaseHTTPMiddleware):
    """
    请求级 DB Session 中间件。

    - 每个请求创建一个 AsyncSession 并挂载到 request.state.db
    - 请求成功自动 commit
    - 出错自动 rollback
    """

    async def dispatch(self, request: Request, call_next):
        session_factory = get_session_factory()
        if session_factory is None:
            return await call_next(request)

        session = session_factory()
        request.state.db = session
        try:
            response = await call_next(request)
            await session.commit()
            return response
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
