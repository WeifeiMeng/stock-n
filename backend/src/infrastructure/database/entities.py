from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class ZtStockEntity(Base):
    __tablename__ = "zt_stock"
    __table_args__ = (Index("idx_zt_stock_code_trade_date", "code", "trade_date"),)

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


class DayStockEntity(Base):
    __tablename__ = "day_stock"
    __table_args__ = (Index("idx_day_stock_code_date", "code", "trade_date"),)

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
    base_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
