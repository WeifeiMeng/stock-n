"""数据仓库实现 —— 替代旧 DAO 层，session 始终显式注入"""
from __future__ import annotations
from typing import Iterable
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo, StockPositionInfo
from .entities import ZtStockEntity, DayStockEntity, StockNEntity, StockPositionEntity
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


class StockPositionRepository:
    @staticmethod
    async def delete_by_trade_date(session: AsyncSession, trade_date: str) -> int:
        from sqlalchemy import delete as sa_delete
        stmt = sa_delete(StockPositionEntity).where(StockPositionEntity.trade_date == trade_date)
        result = await session.execute(stmt)
        return result.rowcount

    @staticmethod
    async def list_by_trade_date(session: AsyncSession, trade_date: str, limit: int = 200) -> list[StockPositionEntity]:
        stmt = (
            select(StockPositionEntity)
            .where(StockPositionEntity.trade_date == trade_date)
            .order_by(StockPositionEntity.buy_amount.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        seen: set[str] = set()
        deduped: list[StockPositionEntity] = []
        for row in rows:
            if row.code not in seen:
                seen.add(row.code)
                deduped.append(row)
        return deduped

    @staticmethod
    async def list_open_before_date(session: AsyncSession, trade_date: str, limit: int = 1000) -> list[StockPositionEntity]:
        stmt = (
            select(StockPositionEntity)
            .where(
                StockPositionEntity.status == "holding",
                StockPositionEntity.trade_date < trade_date,
            )
            .order_by(StockPositionEntity.trade_date, StockPositionEntity.code)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def insert_many(session: AsyncSession, positions: Iterable[StockPositionInfo]) -> int:
        entities = [
            StockPositionEntity(
                code=p.code, name=p.name, trade_date=p.trade_date,
                base_price=p.base_price, highest_price=p.highest_price,
                lowest_price=p.lowest_price, buy_price=p.buy_price,
                buy_lots=p.buy_lots, buy_shares=p.buy_shares,
                buy_amount=p.buy_amount, buy_level=p.buy_level,
                sell_date=p.sell_date, sell_price=p.sell_price,
                sell_amount=p.sell_amount, profit_amount=p.profit_amount,
                profit_rate=p.profit_rate, profit_status=p.profit_status,
                exit_reason=p.exit_reason, status=p.status,
            )
            for p in positions
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)

    @staticmethod
    async def close_position(session: AsyncSession, sold: StockPositionInfo) -> int:
        stmt = (
            update(StockPositionEntity)
            .where(
                StockPositionEntity.code == sold.code,
                StockPositionEntity.trade_date == sold.trade_date,
                StockPositionEntity.status == "holding",
            )
            .values(
                sell_date=sold.sell_date,
                sell_price=sold.sell_price,
                sell_amount=sold.sell_amount,
                profit_amount=sold.profit_amount,
                profit_rate=sold.profit_rate,
                profit_status=sold.profit_status,
                exit_reason=sold.exit_reason,
                status="closed",
            )
        )
        result = await session.execute(stmt)
        return result.rowcount


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
            StockPositionEntity.__table__,
        ])
        await _ensure_stock_position_columns(conn)


async def _ensure_stock_position_columns(conn) -> None:
    dialect = conn.dialect.name
    if dialect != "mysql":
        return

    result = await conn.exec_driver_sql("SHOW COLUMNS FROM stock_position")
    current_columns = {row[0] for row in result}
    missing_columns = {
        "buy_level": "VARCHAR(8) NOT NULL DEFAULT 'B1'",
        "sell_date": "VARCHAR(10) NOT NULL DEFAULT ''",
        "sell_price": "FLOAT NOT NULL DEFAULT 0",
        "sell_amount": "FLOAT NOT NULL DEFAULT 0",
        "profit_amount": "FLOAT NOT NULL DEFAULT 0",
        "profit_rate": "FLOAT NOT NULL DEFAULT 0",
        "profit_status": "VARCHAR(16) NOT NULL DEFAULT ''",
        "exit_reason": "VARCHAR(16) NOT NULL DEFAULT ''",
    }
    for column, definition in missing_columns.items():
        if column in current_columns:
            continue
        await conn.exec_driver_sql(f"ALTER TABLE stock_position ADD COLUMN {column} {definition}")
