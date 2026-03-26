"""
根据日期查询 zt_stock 数据并打印。

用法:
    python scripts/query_zt_stock.py --date 2026-03-24
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.dao import ZtStockDAO
from src.middleware import close_mysql_engine
from src.stock_service.ztapi import get_day_detail


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查询 zt_stock 数据")
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
    rows = await ZtStockDAO.list_by_trade_date(target_date)
    if not rows:
        print(f"[INFO] {target_date} 无 zt_stock 记录。")
        return

    # 计算 target_date 前 30 天的日期
    start_date_obj = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=30)
    start_date_yyyymmdd = start_date_obj.strftime("%Y%m%d")
    target_date_yyyymmdd = target_date.replace("-", "")

    # 遍历所有涨停股，取每只股票的日线
    for r in rows[:1]:
        day_info = await get_day_detail(
            start_date_yyyymmdd, target_date_yyyymmdd, r.code, r.name
        )
        print(f"code={r.code}  name={r.name}  日线共 {len(day_info)} 条")


async def main() -> None:
    args = _parse_args()
    target_date = _resolve_date(args.date)
    try:
        await _run(target_date)
    finally:
        await close_mysql_engine()


if __name__ == "__main__":
    os.environ.get("MYSQL_DSN")
    asyncio.run(main())
