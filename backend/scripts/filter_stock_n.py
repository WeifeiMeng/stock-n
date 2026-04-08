"""
N 规则完整筛选流程：
1. 获取前一交易日涨停股票，过滤 ST/*ST/北交所，存入 zt_stock 表
2. 批量获取所有涨停股票的日线数据（45天），存入 day_stock 表
3. 从 zt_stock 读取数据，过滤目标日未涨停/跌停的股票（优先从 day_stock 读取）
4. 应用规则过滤：
   - 规则4：涨停前 7 个交易日无跌停、无连续涨停
   - 规则5：涨停前 30 个交易日内有涨停记录
5. 补全日线详情，存入 stock_n 表

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
# 工具函数：获取前 n 个工作日
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
# 步骤 2：批量获取日线数据并写入 day_stock 表
# ----------------------------------------------------------------------
async def batch_fetch_and_save_day_stocks(zt_list: list[ZtStockInfo], zt_date: str) -> None:
    """
    批量获取所有股票的日线数据（从zt_date往前45个日历天），存入 day_stock 表。
    先查数据库已存在的记录，避免重复写入。
    """
    zt_date_yyyymmdd = zt_date.replace('-', '')
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=45)
    start_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    codes = [s.code for s in zt_list]
    session_factory = get_session_factory()

    # 先查询数据库已存在的记录
    async with session_factory() as session:
        existing = await DayStockDAO.list_by_codes_and_date_range(
            session, codes, start_yyyymmdd, zt_date_yyyymmdd
        )
        existing_set = {(d.code, d.trade_date) for d in existing}
        logger.info("day_stock 表已存在 %d 条记录", len(existing_set))

    # 需要从 API 获取的股票列表
    to_fetch = [s for s in zt_list if not any(s.code == c for c, _ in existing_set)]

    if not to_fetch:
        logger.info("所有股票的日线数据已存在于 day_stock 表")
        return

    logger.info("需要从 API 获取 %d 只股票的日线数据", len(to_fetch))

    # 批量从 API 获取并写入
    for stock in to_fetch:
        day_list = await get_day_detail(start_yyyymmdd, zt_date_yyyymmdd, stock.code, stock.name)
        if not day_list:
            continue

        # 只写入数据库中没有的记录
        to_insert = [d for d in day_list if (d.code, d.date) not in existing_set]
        if to_insert:
            async with session_factory() as session:
                await DayStockDAO.insert_many(session, to_insert)
                await session.commit()

    logger.info("日线数据批量写入 day_stock 表完成")


# ----------------------------------------------------------------------
# 工具函数：优先从 day_stock 读取日线数据，没有则调 API
# ----------------------------------------------------------------------
async def get_day_data_cached(
    code: str, name: str, start_yyyymmdd: str, end_yyyymmdd: str
) -> list[DayStockInfo]:
    """
    获取股票日线数据，优先从 day_stock 表读取，数据库没有则调 API 并保存。
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        db_days = await DayStockDAO.list_by_codes_and_date_range(
            session, [code], start_yyyymmdd, end_yyyymmdd
        )

    # 转换为 DayStockInfo
    day_stock_infos = [
        DayStockInfo(
            code=d.code,
            name=d.name or name,
            market=d.market or "",
            industry=d.industry or "",
            start_pri=d.start_pri,
            end_pri=d.end_pri,
            highest_pri=d.highest_pri,
            lowest_pri=d.lowest_pri,
            date=d.trade_date,
        )
        for d in db_days
    ]

    # 如果数据库有足够数据，直接返回
    if len(day_stock_infos) >= 2:
        return day_stock_infos

    # 数据库没有，调 API
    api_days = await get_day_detail(start_yyyymmdd, end_yyyymmdd, code, name)
    if not api_days:
        return day_stock_infos

    # 保存到数据库
    async with session_factory() as session:
        await DayStockDAO.insert_many(session, api_days)
        await session.commit()

    return api_days


# ----------------------------------------------------------------------
# 步骤 3：从 zt_stock 表读取，过滤目标日未涨停/跌停的股票
# ----------------------------------------------------------------------
async def filter_by_target_day(
    prev_workday: str, target_date: str, zt_list: list[ZtStockInfo]
) -> list[ZtStockInfo]:
    """
    读取 zt_list 中股票在 target_date 的行情，过滤出目标日未涨停且未跌停的股票。
    """
    prev_yyyymmdd = prev_workday.replace('-', '')
    target_yyyymmdd = target_date.replace('-', '')
    result: list[ZtStockInfo] = []

    for stock in zt_list:
        day_list = await get_day_data_cached(stock.code, stock.name, prev_yyyymmdd, target_yyyymmdd)
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
# 步骤 4：应用规则4、规则5 过滤
# ----------------------------------------------------------------------
async def rule_no_zt_no_dt(zt_list: list[ZtStockInfo], zt_date: str) -> list[ZtStockInfo]:
    """规则4：过滤涨停前 7 个交易日有跌停或连续涨停的股票"""
    zt_date_yyyymmdd = zt_date.replace('-', '')
    # 往前取14个日历天，确保能覆盖7个以上的交易日后
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=14)
    start_date_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: list[ZtStockInfo] = []
    for stock in zt_list:
        day_list = await get_day_data_cached(stock.code, stock.name, start_date_yyyymmdd, zt_date_yyyymmdd)
        if len(day_list) < 8:
            continue

        # day_list 是按时间排序的（ oldest -> newest）
        # 取最后8个元素，其中 day_list[-1] 是涨停日，前7个是涨停前的7个交易日
        check_days = day_list[-8:-1]  # 涨停日之前的7个交易日
        if len(check_days) != 7:
            continue

        has_dt = False
        consecutive_zt = 0
        for i in range(7):
            prev_pri = check_days[i - 1].end_pri if i > 0 else 0
            curr_pri = check_days[i].end_pri
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
    # 往前取45个日历天，确保能覆盖30个以上的交易日
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=45)
    start_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: list[ZtStockInfo] = []
    for stock in zt_list:
        day_list = await get_day_data_cached(stock.code, stock.name, start_yyyymmdd, zt_date_yyyymmdd)
        if len(day_list) < 2:
            continue

        # 取最后30个交易日（不包含涨停日本身），检查这30天内是否有涨停
        # day_list[-1] 是涨停日，day_list[:-1] 是涨停前的所有数据
        # 取最近30个交易日
        pre_days = day_list[-31:-1] if len(day_list) >= 31 else day_list[:-1]
        if len(pre_days) < 2:
            continue

        has_zt = False
        # 检查所有相邻的交易日对
        for i in range(1, len(pre_days)):
            if _is_zt(pre_days[i - 1].end_pri, pre_days[i].end_pri):
                has_zt = True
                break
        if has_zt:
            result.append(stock)
    return result


# ----------------------------------------------------------------------
# 步骤 5：构建 StockNInfo 并存入 stock_n 表
# ----------------------------------------------------------------------
async def save_stock_n(
    stocks: list[ZtStockInfo], target_date: str, prev_workday: str
) -> int:
    """获取日线详情，构造 StockNInfo，写入 stock_n 表"""
    # 获取 target_date 前第二个交易日作为 base_price 参考日
    base_date = await _get_n_prev_workday(target_date, 2)
    base_yyyymmdd = base_date.replace('-', '')
    prev_yyyymmdd = prev_workday.replace('-', '')
    target_yyyymmdd = target_date.replace('-', '')

    stock_n_list: list[StockNInfo] = []
    for stock in stocks:
        day_list = await get_day_data_cached(stock.code, stock.name, base_yyyymmdd, target_yyyymmdd)
        if len(day_list) < 2:
            continue

        # 找到 base_date、target_date 对应的日线数据
        base_info = None
        target_info = None
        for day in day_list:
            if day.date == base_date:
                base_info = day
            if day.date == target_date:
                target_info = day
        if base_info is None or target_info is None:
            continue

        zt_day_info = day_list[-1]   # 涨停日

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
            base_price=base_info.end_pri,
        ))

    if not stock_n_list:
        return 0

    session_factory = get_session_factory()
    async with session_factory() as session:
        inserted = await StockNDAO.insert_many(session, stock_n_list)
        await session.commit()
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

        # Step 2.5: 批量获取所有股票的日线数据并存入 day_stock 表
        await batch_fetch_and_save_day_stocks(zt_list, prev_workday)

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

    finally:
        await close_mysql_engine()


def main() -> None:
    args = _parse_args()
    target_date = _resolve_date(args.date)
    asyncio.run(_run(target_date))


if __name__ == "__main__":
    os.environ.get("MYSQL_DSN")
    main()
