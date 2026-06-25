"""数据仓库实现 —— 替代旧 DAO 层，session 始终显式注入"""
from __future__ import annotations
from typing import Iterable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo
from .entities import ZtStockEntity, DayStockEntity, StockNEntity
from .base import Base


class ZtStockRepository:
    @staticmethod
    async def list_by_trade_date(session: AsyncSession, trade_date: str, limit: int = 200) -> list[ZtStockEntity]:
        stmt = (
            select(ZtStockEntity)
            .where(ZtStockEntity.trade_date == trade_date)
            .order_by(ZtStockEntity.zf.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[ZtStockInfo], trade_date: str) -> int:
        entities = [
            ZtStockEntity(
                code=s.code, name=s.name, pri=s.pri, zf=s.zf, cje=s.cje,
                lt=s.lt, zsz=s.zsz, hs=s.hs, fbt=s.fbt, lbt=s.lbt,
                zj=s.zj, zbc=s.zbc, lbc=s.lbc, tj=s.tj, trade_date=trade_date,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


class DayStockRepository:
    @staticmethod
    async def list_by_codes_and_date_range(
        session: AsyncSession, codes: list[str], start_date: str, end_date: str
    ) -> list[DayStockEntity]:
        stmt = (
            select(DayStockEntity)
            .where(
                DayStockEntity.code.in_(codes),
                DayStockEntity.trade_date >= start_date,
                DayStockEntity.trade_date <= end_date,
            )
            .order_by(DayStockEntity.trade_date)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        seen: set[tuple[str, str]] = set()
        deduped: list[DayStockEntity] = []
        for row in rows:
            key = (row.code, row.trade_date)
            if key not in seen:
                seen.add(key)
                deduped.append(row)
        return deduped

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[DayStockInfo]) -> int:
        entities = [
            DayStockEntity(
                code=s.code, name=s.name, market=s.market, industry=s.industry,
                start_pri=s.start_pri, end_pri=s.end_pri,
                highest_pri=s.highest_pri, lowest_pri=s.lowest_pri,
                trade_date=s.date,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


class StockNRepository:
    @staticmethod
    async def delete_by_trade_date(session: AsyncSession, trade_date: str) -> int:
        from sqlalchemy import delete as sa_delete
        stmt = sa_delete(StockNEntity).where(StockNEntity.trade_date == trade_date)
        result = await session.execute(stmt)
        return result.rowcount

    @staticmethod
    async def list_by_trade_date(session: AsyncSession, trade_date: str, limit: int = 200) -> list[StockNEntity]:
        stmt = (
            select(StockNEntity)
            .where(StockNEntity.trade_date == trade_date)
            .order_by(StockNEntity.n.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        seen: set[str] = set()
        deduped: list[StockNEntity] = []
        for row in rows:
            if row.code not in seen:
                seen.add(row.code)
                deduped.append(row)
        return deduped

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[StockNInfo]) -> int:
        entities = [
            StockNEntity(
                code=s.code, name=s.name, market=s.market, industry=s.industry,
                start_pri=s.start_pri, end_pri=s.end_pri,
                highest_pri=s.highest_pri, lowest_pri=s.lowest_pri,
                trade_date=s.date, zt=s.zt, dt=s.dt, n=s.n, base_price=s.base_price,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


async def init_all_tables() -> None:
    """创建所有数据表（幂等，仅当引擎已配置时执行）"""
    from .connection import get_mysql_engine
    engine = get_mysql_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[
            ZtStockEntity.__table__,
            DayStockEntity.__table__,
            StockNEntity.__table__,
        ])
