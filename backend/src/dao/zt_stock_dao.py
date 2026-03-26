"""
ZtStockInfo 的 DAO 与 ORM 模型。
"""
from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import Float, Index, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.middleware import get_session_factory
from src.vo.stock import ZtStockInfo


class Base(DeclarativeBase):
    pass


class ZtStockEntity(Base):
    __tablename__ = "zt_stock"
    __table_args__ = (
        Index("idx_zt_stock_code_trade_date", "code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zf: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cje: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zsz: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fbt: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    lbt: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    zj: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zbc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lbc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tj: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")


class ZtStockDAO:
    @staticmethod
    async def create_table(engine: AsyncEngine) -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=[ZtStockEntity.__table__])

    @staticmethod
    async def insert_one(
        session: AsyncSession, stock: ZtStockInfo, trade_date: str
    ) -> ZtStockEntity:
        entity = ZtStockEntity(
            code=stock.code,
            name=stock.name,
            pri=stock.pri,
            zf=stock.zf,
            cje=stock.cje,
            lt=stock.lt,
            zsz=stock.zsz,
            hs=stock.hs,
            fbt=stock.fbt,
            lbt=stock.lbt,
            zj=stock.zj,
            zbc=stock.zbc,
            lbc=stock.lbc,
            tj=stock.tj,
            trade_date=trade_date,
        )
        session.add(entity)
        await session.flush()
        return entity

    @staticmethod
    async def insert_many(
        session: AsyncSession, stocks: Iterable[ZtStockInfo], trade_date: str
    ) -> int:
        entities = [
            ZtStockEntity(
                code=s.code,
                name=s.name,
                pri=s.pri,
                zf=s.zf,
                cje=s.cje,
                lt=s.lt,
                zsz=s.zsz,
                hs=s.hs,
                fbt=s.fbt,
                lbt=s.lbt,
                zj=s.zj,
                zbc=s.zbc,
                lbc=s.lbc,
                tj=s.tj,
                trade_date=trade_date,
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
    ) -> List[ZtStockEntity]:
        # 兼容两种调用方式：
        # 1) list_by_trade_date(session, trade_date, limit)
        # 2) list_by_trade_date(trade_date, limit=...)
        if isinstance(session_or_trade_date, AsyncSession):
            if trade_date is None:
                raise ValueError("当第一个参数是 session 时，trade_date 不能为空。")
            return await ZtStockDAO._list_by_trade_date_with_session(
                session_or_trade_date, trade_date, limit
            )

        resolved_trade_date = session_or_trade_date
        session_factory = get_session_factory()
        if session_factory is None:
            raise RuntimeError(
                "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
            )
        async with session_factory() as session:
            return await ZtStockDAO._list_by_trade_date_with_session(
                session, resolved_trade_date, limit
            )

    @staticmethod
    async def _list_by_trade_date_with_session(
        session: AsyncSession, trade_date: str, limit: int
    ) -> List[ZtStockEntity]:
        stmt = (
            select(ZtStockEntity)
            .where(ZtStockEntity.trade_date == trade_date)
            .order_by(ZtStockEntity.zf.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
