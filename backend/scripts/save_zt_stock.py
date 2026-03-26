"""
拉取指定日期涨停池数据并保存到 MySQL 的 zt_stock 表。

用法:
    python scripts/save_zt_stock.py --date 2026-03-24
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# 允许在 backend 目录直接运行脚本时导入 src
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.dao import ZtStockDAO, init_all_tables
from src.middleware import close_mysql_engine, get_session_factory
from src.stock_service.ztapi import get_zt_stock_list
from src.service.n_calculate import rule_filter_st_bj


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="保存涨停池数据到 MySQL zt_stock")
    parser.add_argument(
        "--date",
        required=False,
        help="交易日期，格式 YYYY-MM-DD，默认今天",
    )
    return parser.parse_args()


def _resolve_date(date_text: str | None) -> str:
    if not date_text:
        return datetime.now().strftime("%Y-%m-%d")
    datetime.strptime(date_text, "%Y-%m-%d")
    return date_text


async def _run(target_date: str) -> None:
    try:
        await init_all_tables()

        session_factory = get_session_factory()
        if session_factory is None:
            raise RuntimeError(
                "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
            )

        zt_list = await get_zt_stock_list(target_date)
        zt_list = rule_filter_st_bj(zt_list)
        if not zt_list:
            print(f"[INFO] {target_date} 无可入库涨停池数据。")
            return

        async with session_factory() as session:
            inserted = await ZtStockDAO.insert_many(session, zt_list, target_date)
            await session.commit()

        print(f"[INFO] {target_date} 入库完成，写入 zt_stock {inserted} 条记录。")
    finally:
        # 在同一个 event loop 中释放连接池，避免 loop 关闭后清理报错
        await close_mysql_engine()


def main() -> None:
    args = _parse_args()
    target_date = _resolve_date(args.date)
    asyncio.run(_run(target_date))


if __name__ == "__main__":
    # 可选：从 .env 读取时，这里只保持环境变量直读，不做额外依赖引入
    os.environ.get("MYSQL_DSN")
    main()
