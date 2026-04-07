"""
N 规则完整筛选流程：
1. 获取前一交易日涨停股票，过滤 ST/*ST/北交所，存入 zt_stock 表
2. 从 zt_stock 读取数据，过滤目标日未涨停/跌停的股票
3. 应用规则过滤：
   - 规则4：涨停前 7 个交易日无跌停、无连续涨停
   - 规则5：涨停前 30 个交易日内有涨停记录
4. 补全日线详情，存入 stock_n 表

用法:
    python scripts/filter_stock_n.py --date 2026-03-24
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.dao import ZtStockDAO, StockNDAO, DayStockDAO, init_all_tables
from src.middleware import close_mysql_engine, get_session_factory
from src.service.n_calculate import (
    _get_prev_workday,
    _is_zt,
    _is_dt,
    ZT_THRESHOLD,
    DT_THRESHOLD,
    ZT_PCT,
)
from src.stock_service.ztapi import get_day_detail, get_zt_stock_list
from src.stock_service.tools import get_market
from src.vo.stock import ZtStockInfo, StockNInfo, DayStockInfo


logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="N 规则完整筛选")
    parser.add_argument(
        "--date",
        required=False,
        help="目标交易日期，格式 YYYY-MM-DD，默认今天",
    )
    return parser.parse_args()


def _resolve_date(date_text: str | None) -> str:
    if not date_text:
        return datetime.now().strftime("%Y-%m-%d")
    datetime.strptime(date_text, "%Y-%m-%d")
    return date_text


# ----------------------------------------------------------------------
# 步骤 1：从 API 拉取前一交易日涨停数据，过滤后写入 zt_stock 表
# ----------------------------------------------------------------------
async def fetch_and_save_zt_stocks(prev_workday: str) -> list[ZtStockInfo]:
    """从 API 获取前一交易日涨停数据，过滤 ST/*ST/北交所，存入 zt_stock 表"""
    zt_list = await get_zt_stock_list(prev_workday)
    logger.info("API 返回 %s 涨停股票 %d 只", prev_workday, len(zt_list))

    # 过滤 ST、*ST、北交所
    zt_list = [
        s for s in zt_list
        if not (s.name.startswith('ST') or s.name.startswith('*ST'))
        and not (s.code.startswith('8') or s.code.startswith('4'))
        and get_market(s.code) is not None
    ]
    logger.info("过滤 ST/*ST/北交所后剩余 %d 只", len(zt_list))

    if not zt_list:
        return []

    session_factory = get_session_factory()
    async with session_factory() as session:
        inserted = await ZtStockDAO.insert_many(session, zt_list, prev_workday)
        await session.commit()
    logger.info("写入 zt_stock 表 %d 条", inserted)

    return zt_list


# ----------------------------------------------------------------------
# 步骤 2：从 zt_stock 表读取，过滤目标日未涨停/跌停的股票
# ----------------------------------------------------------------------
async def filter_by_target_day(
    prev_workday: str, target_date: str, zt_list: list[ZtStockInfo]
) -> list[ZtStockInfo]:
    """
    读取 zt_list 中股票在 target_date 的行情，过滤出目标日未涨停且未跌停的股票。
    同时将目标日行情数据一并返回。
    """
    prev_yyyymmdd = prev_workday.replace('-', '')
    target_yyyymmdd = target_date.replace('-', '')
    result: list[ZtStockInfo] = []

    for stock in zt_list:
        day_list = await get_day_detail(prev_yyyymmdd, target_yyyymmdd, stock.code, stock.name)
        if len(day_list) < 2:
            continue
        lastday_info, today_info = day_list[0], day_list[1]
        if lastday_info.end_pri <= 0:
            continue
        if (today_info.end_pri / lastday_info.end_pri >= ZT_THRESHOLD) or \
           (today_info.end_pri / lastday_info.end_pri <= DT_THRESHOLD):
            continue
        result.append(stock)

    logger.info("过滤目标日涨停/跌停后剩余 %d 只", len(result))
    return result


# ----------------------------------------------------------------------
# 步骤 3：应用规则4、规则5 过滤
# ----------------------------------------------------------------------
async def rule_no_zt_no_dt(zt_list: list[ZtStockInfo], zt_date: str) -> list[ZtStockInfo]:
    """规则4：过滤涨停前 7 个交易日有跌停或连续涨停的股票"""
    zt_date_yyyymmdd = zt_date.replace('-', '')
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=10)
    start_date_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: list[ZtStockInfo] = []
    for stock in zt_list:
        day_list = await get_day_detail(start_date_yyyymmdd, zt_date_yyyymmdd, stock.code, stock.name)
        if len(day_list) < 9:
            continue
        has_dt = False
        consecutive_zt = 0
        for i in range(8):
            prev_pri = day_list[-9 + i].end_pri
            curr_pri = day_list[-8 + i].end_pri
            if prev_pri <= 0:
                continue
            if _is_dt(prev_pri, curr_pri):
                has_dt = True
                break
            if _is_zt(prev_pri, curr_pri):
                consecutive_zt += 1
                if consecutive_zt >= 2:
                    break
            else:
                consecutive_zt = 0
        if not has_dt and consecutive_zt < 2:
            result.append(stock)
    return result


async def rule_zt_30_days(zt_list: list[ZtStockInfo], zt_date: str) -> list[ZtStockInfo]:
    """规则5：过滤涨停前 30 个交易日内没有涨停过的股票"""
    zt_date_yyyymmdd = zt_date.replace('-', '')
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=60)
    start_date_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: list[ZtStockInfo] = []
    for stock in zt_list:
        day_list = await get_day_detail(start_date_yyyymmdd, zt_date_yyyymmdd, stock.code, stock.name)
        if len(day_list) < 2:
            continue
        # 包含 zt_date：day_list[-30:] 取最近 30 天（T-29 到 T）
        pre_days = day_list[-30:] if len(day_list) >= 30 else day_list[:]
        if len(pre_days) < 2:
            continue
        has_zt = False
        for i in range(1, min(len(pre_days), 30)):
            if _is_zt(pre_days[i - 1].end_pri, pre_days[i].end_pri):
                has_zt = True
                break
        if has_zt:
            result.append(stock)
    return result


# ----------------------------------------------------------------------
# 步骤 4：构建 StockNInfo 并存入 stock_n 表
# ----------------------------------------------------------------------
async def save_stock_n(
    stocks: list[ZtStockInfo], target_date: str, prev_workday: str
) -> int:
    """获取日线详情，构造 StockNInfo，写入 stock_n 表"""
    prev_yyyymmdd = prev_workday.replace('-', '')
    target_yyyymmdd = target_date.replace('-', '')

    stock_n_list: list[StockNInfo] = []
    for stock in stocks:
        day_list = await get_day_detail(prev_yyyymmdd, target_yyyymmdd, stock.code, stock.name)
        if len(day_list) < 2:
            continue

        zt_day_info = day_list[-1]   # 涨停日
        target_info = day_list[-2]   # 目标日

        market = get_market(stock.code) or ""

        stock_n_list.append(StockNInfo(
            code=stock.code,
            name=stock.name,
            market=market,
            industry="",
            start_pri=target_info.start_pri,
            end_pri=target_info.end_pri,
            highest_pri=target_info.highest_pri,
            lowest_pri=target_info.lowest_pri,
            date=target_date,
            zt=_is_zt(zt_day_info.end_pri, target_info.end_pri),
            dt=_is_dt(zt_day_info.end_pri, target_info.end_pri),
            n=stock.lbc,
        ))

    if not stock_n_list:
        return 0

    session_factory = get_session_factory()
    async with session_factory() as session:
        inserted = await StockNDAO.insert_many(session, stock_n_list)
        await session.commit()
    return inserted


# ----------------------------------------------------------------------
# 步骤 5：保存 target_date 前两个交易日的日线数据到 day_stock 表
# ----------------------------------------------------------------------
async def _get_n_prev_workday(date: str, n: int) -> str:
    """获取 date 的前 n 个工作日"""
    import chinese_calendar
    date_obj = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=None)
    prev_day = date_obj - timedelta(days=1)
    count = 0
    while count < n:
        if chinese_calendar.is_workday(prev_day.date()):
            count += 1
            if count == n:
                break
        prev_day = prev_day - timedelta(days=1)
    return prev_day.strftime('%Y-%m-%d')


async def save_day_stocks(stocks: list[ZtStockInfo], target_date: str) -> int:
    """保存 target_date 前两个交易日的日线数据到 day_stock 表"""
    ref_date = await _get_n_prev_workday(target_date, 2)
    ref_yyyymmdd = ref_date.replace('-', '')
    # 取 ref_date 前后各几天，确保能拿到 ref_date 的数据
    start_obj = datetime.strptime(ref_date, '%Y-%m-%d') - timedelta(days=5)
    start_yyyymmdd = start_obj.strftime('%Y%m%d')

    day_stock_list: list[DayStockInfo] = []
    for stock in stocks:
        day_list = await get_day_detail(start_yyyymmdd, ref_yyyymmdd, stock.code, stock.name)
        # 从 day_list 中找到 ref_date 当天的数据
        for day in day_list:
            if day.date == ref_date:
                day_stock_list.append(day)
                break

    if not day_stock_list:
        return 0

    session_factory = get_session_factory()
    async with session_factory() as session:
        inserted = await DayStockDAO.insert_many(session, day_stock_list)
        await session.commit()
    logger.info("写入 day_stock 表 %d 条 (%s 数据)", inserted, ref_date)
    return inserted


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
async def _run(target_date: str) -> None:
    try:
        await init_all_tables()

        session_factory = get_session_factory()
        if session_factory is None:
            raise RuntimeError(
                "MySQL 未配置，请设置 MYSQL_DSN 或 MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE。"
            )

        # Step 1: 前一交易日（涨停日）
        prev_workday = _get_prev_workday(target_date)
        logger.info(f"目标日期: {target_date}，前一交易日(涨停日): {prev_workday}")

        # Step 2: 从 API 拉取并写入 zt_stock 表
        zt_list = await fetch_and_save_zt_stocks(prev_workday)
        if not zt_list:
            print(f"[INFO] {prev_workday} 无涨停数据，跳过。")
            return

        # Step 3: 过滤目标日未涨停/跌停
        zt_list = await filter_by_target_day(prev_workday, target_date, zt_list)
        logger.info(f"步骤3 - 过滤目标日涨停/跌停后剩余 %d 只", len(zt_list))
        if not zt_list:
            print(f"[INFO] {target_date} 过滤后无股票。")
            return

        # Step 4: 规则4 — 涨停前7日无跌停、无连续涨停
        zt_list = await rule_no_zt_no_dt(zt_list, prev_workday)
        logger.info(f"步骤4 - 过滤近7日有跌停/连续涨停后剩余 %d 只", len(zt_list))

        # Step 5: 规则5 — 涨停前30日有涨停
        zt_list = await rule_zt_30_days(zt_list, prev_workday)
        logger.info(f"步骤5 - 过滤近30日无涨停后剩余 %d 只", len(zt_list))
        if not zt_list:
            print(f"[INFO] {target_date} 规则筛选后无股票。")
            return

        # Step 6: 写入 stock_n 表
        inserted = await save_stock_n(zt_list, target_date, prev_workday)
        print(f"[INFO] {target_date} 入库完成：zt_stock {len(zt_list)} 条，stock_n {inserted} 条。")

        # Step 7: 写入 day_stock 表（target_date 前两个交易日）
        await save_day_stocks(zt_list, target_date)

    finally:
        await close_mysql_engine()


def main() -> None:
    args = _parse_args()
    target_date = _resolve_date(args.date)
    asyncio.run(_run(target_date))


if __name__ == "__main__":
    os.environ.get("MYSQL_DSN")
    main()
