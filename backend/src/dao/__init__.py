"""
DAO 层统一导出与初始化。
"""
from __future__ import annotations

from src.middleware import get_mysql_engine

from .day_stock_dao import DayStockDAO
from .stock_n_dao import StockNDAO
from .zt_stock_dao import ZtStockDAO


async def init_all_tables() -> None:
    """
    初始化 DAO 层所需的全部数据表。
    """
    engine = get_mysql_engine()
    if engine is None:
        return

    await DayStockDAO.create_table(engine)
    await StockNDAO.create_table(engine)
    await ZtStockDAO.create_table(engine)


__all__ = ["DayStockDAO", "StockNDAO", "ZtStockDAO", "init_all_tables"]
