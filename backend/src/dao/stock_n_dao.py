"""
StockNInfo 的 DAO 与 ORM 模型。
"""
from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import Boolean, Index, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.middleware import get_session_factory
from src.vo.stock import StockNInfo


class Base(DeclarativeBase):
    pass


class StockNEntity(Base):
    __tablename__ = "stock_n"
    __table_args__ = (
        Index("idx_stock_n_code_date", "code", "trade_date"),
        Index("idx_stock_n_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    market: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    start_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    end_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    highest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lowest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    zt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StockNDAO:
    @staticmethod
    async def create_table(engine: AsyncEngine) -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=[StockNEntity.__table__])

    @staticmethod
    async def insert_one(session: AsyncSession, stock: StockNInfo) -> StockNEntity:
        entity = StockNEntity(
            code=stock.code,
            name=stock.name,
            market=stock.market,
            industry=stock.industry,
            start_pri=stock.start_pri,
            end_pri=stock.end_pri,
            highest_pri=stock.highest_pri,
            lowest_pri=stock.lowest_pri,
            trade_date=stock.date,
            zt=stock.zt,
            dt=stock.dt,
            n=stock.n,
        )
        session.add(entity)
        await session.flush()
        return entity

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[StockNInfo]) -> int:
        entities = [
            StockNEntity(
                code=s.code,
                name=s.name,
                market=s.market,
                industry=s.industry,
                start_pri=s.start_pri,
                end_pri=s.end_pri,
                highest_pri=s.highest_pri,
                lowest_pri=s.lowest_pri,
                trade_date=s.date,
                zt=s.zt,
                dt=s.dt,
                n=s.n,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)

    @staticmethod
    async def list_by_trade_date(
        session_or_trade_date: AsyncSession | str,
        trade_date: str | None = None,
        limit: int = 200,
    ) -> List[StockNEntity]:
        # 兼容两种调用方式：
        # 1) list_by_trade_date(session, trade_date, limit)
        # 2) list_by_trade_date(trade_date, limit=...)
        if isinstance(session_or_trade_date, AsyncSession):
            if trade_date is None:
                raise ValueError("当第一个参数是 session 时，trade_date 不能为空。")
            return await StockNDAO._list_by_trade_date_with_session(
                session_or_trade_date, trade_date, limit
            )

        resolved_trade_date = session_or_trade_date
        session_factory = get_session_factory()
        if session_factory is None:
            raise RuntimeError(
                "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
            )
        async with session_factory() as session:
            return await StockNDAO._list_by_trade_date_with_session(
                session, resolved_trade_date, limit
            )

    @staticmethod
    async def _list_by_trade_date_with_session(
        session: AsyncSession, trade_date: str, limit: int
    ) -> List[StockNEntity]:
        stmt = (
            select(StockNEntity)
            .where(StockNEntity.trade_date == trade_date)
            .order_by(StockNEntity.n.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_by_code(
        session_or_code: AsyncSession | str,
        code: str | None = None,
        limit: int = 100,
    ) -> List[StockNEntity]:
        # 兼容两种调用方式：
        # 1) list_by_code(session, code, limit)
        # 2) list_by_code(code, limit=...)
        if isinstance(session_or_code, AsyncSession):
            if code is None:
                raise ValueError("当第一个参数是 session 时，code 不能为空。")
            return await StockNDAO._list_by_code_with_session(session_or_code, code, limit)

        resolved_code = session_or_code
        session_factory = get_session_factory()
        if session_factory is None:
            raise RuntimeError(
                "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
            )
        async with session_factory() as session:
            return await StockNDAO._list_by_code_with_session(session, resolved_code, limit)

    @staticmethod
    async def _list_by_code_with_session(
        session: AsyncSession, code: str, limit: int
    ) -> List[StockNEntity]:
        stmt = (
            select(StockNEntity)
            .where(StockNEntity.code == code)
            .order_by(StockNEntity.trade_date.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
