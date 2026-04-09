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

# API 请求计数器
class ApiCallCounter:
    _day_detail_count: int = 0
    _zt_stock_list_count: int = 0

    @classmethod
    def inc_day_detail(cls):
        cls._day_detail_count += 1

    @classmethod
    def inc_zt_stock_list(cls):
        cls._zt_stock_list_count += 1

    @classmethod
    def get_day_detail_count(cls) -> int:
        return cls._day_detail_count

    @classmethod
    def get_zt_stock_list_count(cls) -> int:
        return cls._zt_stock_list_count

    @classmethod
    def reset(cls):
        cls._day_detail_count = 0
        cls._zt_stock_list_count = 0


# 带计数的 API 调用包装函数
async def counted_get_day_detail(start_date: str, end_date: str, code: str, name: str) -> list[DayStockInfo]:
    ApiCallCounter.inc_day_detail()
    return await get_day_detail(start_date, end_date, code, name)

async def counted_get_zt_stock_list(date: str) -> list[ZtStockInfo]:
    ApiCallCounter.inc_zt_stock_list()
    return await get_zt_stock_list(date)


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
    """
    获取前一交易日涨停数据，优先从 zt_stock 表读取，没有则调 API 获取并写入数据库。
    """
    # 先从数据库查询
    session_factory = get_session_factory()
    async with session_factory() as session:
        db_zt_list = await ZtStockDAO.list_by_trade_date(session, prev_workday)

    if db_zt_list:
        # 数据库有数据，直接使用
        zt_list = [
            ZtStockInfo(
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
            )
            for s in db_zt_list
        ]
        logger.info("从 zt_stock 表读取 %s 涨停股票 %d 只", prev_workday, len(zt_list))

        # 过滤 ST、*ST、北交所
        zt_list = [
            s for s in zt_list
            if not (s.name.startswith('ST') or s.name.startswith('*ST'))
            and not (s.code.startswith('8') or s.code.startswith('4'))
            and get_market(s.code) is not None
        ]
        logger.info("过滤 ST/*ST/北交所后剩余 %d 只", len(zt_list))
        return zt_list

    # 数据库没有，调 API
    zt_list = await counted_get_zt_stock_list(prev_workday)
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

    async with session_factory() as session:
        inserted = await ZtStockDAO.insert_many(session, zt_list, prev_workday)
        await session.commit()
    logger.info("写入 zt_stock 表 %d 条", inserted)

    return zt_list


# ----------------------------------------------------------------------
# 工具函数：优先从 day_stock 读取日线数据，没有则调 API
# ----------------------------------------------------------------------
async def get_day_data_cached(
    code: str, name: str, start_yyyymmdd: str, end_yyyymmdd: str
) -> list[DayStockInfo]:
    """
    获取股票日线数据，优先从 day_stock 表读取，数据库没有则调 API 并保存。
    注意：数据库中 trade_date 存储为 'YYYY-MM-DD' 格式，但查询参数是 'YYYYMMDD'，需转换
    如果 API 返回空，则返回空列表
    """
    # 将 'YYYYMMDD' 格式转换为 'YYYY-MM-DD' 格式用于数据库查询
    start_date_fmt = f"{start_yyyymmdd[:4]}-{start_yyyymmdd[4:6]}-{start_yyyymmdd[6:8]}"
    end_date_fmt = f"{end_yyyymmdd[:4]}-{end_yyyymmdd[4:6]}-{end_yyyymmdd[6:8]}"

    session_factory = get_session_factory()
    async with session_factory() as session:
        db_days = await DayStockDAO.list_by_codes_and_date_range(
            session, [code], start_date_fmt, end_date_fmt
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

    # 数据库没有或数据不足，调 API
    api_days = await counted_get_day_detail(start_yyyymmdd, end_yyyymmdd, code, name)
    if not api_days:
        # API 返回空，返回空列表
        return []

    # 保存到数据库
    async with session_factory() as session:
        await DayStockDAO.insert_many(session, api_days)
        await session.commit()

    return api_days


# ----------------------------------------------------------------------
# 步骤 3-5：检查单只股票是否满足所有规则
# ----------------------------------------------------------------------
async def check_stock_all_rules(
    stock: ZtStockInfo, prev_workday: str, target_date: str
) -> bool:
    """
    检查单只股票是否满足所有规则：
    - 步骤3：目标日未涨停未跌停
    - 规则4：涨停前 7 个交易日无跌停、无连续涨停
    - 规则5：涨停前 30 个交易日内有涨停
    返回 True 表示通过所有规则，False 表示未通过
    """
    prev_yyyymmdd = prev_workday.replace('-', '')
    target_yyyymmdd = target_date.replace('-', '')

    # 获取涨停日前7个交易日的数据（用于规则4检查）
    rule4_start_obj = datetime.strptime(prev_workday, '%Y-%m-%d') - timedelta(days=14)
    rule4_start_yyyymmdd = rule4_start_obj.strftime('%Y%m%d')

    # 获取涨停日前30个交易日的数据（用于规则5检查）
    rule5_start_obj = datetime.strptime(prev_workday, '%Y-%m-%d') - timedelta(days=45)
    rule5_start_yyyymmdd = rule5_start_obj.strftime('%Y%m%d')

    # 步骤3：获取目标日日线数据，检查目标日未涨停未跌停
    day_list_3 = await get_day_data_cached(stock.code, stock.name, prev_yyyymmdd, target_yyyymmdd)
    if len(day_list_3) < 2:
        return False
    lastday_info, today_info = day_list_3[0], day_list_3[1]
    if lastday_info.end_pri <= 0:
        return False
    # 目标日涨停或跌停则不符合
    if (today_info.end_pri / lastday_info.end_pri >= ZT_THRESHOLD) or \
       (today_info.end_pri / lastday_info.end_pri <= DT_THRESHOLD):
        return False

    # 规则4：获取涨停日前7个交易日数据，检查无跌停、无连续涨停
    day_list_4 = await get_day_data_cached(stock.code, stock.name, rule4_start_yyyymmdd, prev_yyyymmdd)
    if len(day_list_4) < 8:
        return False
    # day_list[-1] 是涨停日，前7个是涨停前的7个交易日
    check_days = day_list_4[-8:-1]
    if len(check_days) != 7:
        return False

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
        print(f"has_dt: {has_dt}, consecutive_zt: {consecutive_zt}, day: {check_days[i].date}")
        
    if has_dt or consecutive_zt >= 2:
        return False

    # 规则5：获取涨停日前30个交易日数据，检查有涨停记录
    day_list_5 = await get_day_data_cached(stock.code, stock.name, rule5_start_yyyymmdd, prev_yyyymmdd)
    if len(day_list_5) < 2:
        return False
    # 取最后30个交易日（不包含涨停日本身）
    pre_days = day_list_5[-25:-2] if len(day_list_5) >= 25 else day_list_5[:-2]
    if len(pre_days) < 2:
        return False

    has_zt = False
    for i in range(1, len(pre_days)):
        if _is_zt(pre_days[i - 1].end_pri, pre_days[i].end_pri):
            has_zt = True
            break
    if not has_zt:
        return False

    return True


# ----------------------------------------------------------------------
# 批量检查所有股票是否满足规则
# ----------------------------------------------------------------------
async def filter_stocks_by_all_rules(
    zt_list: list[ZtStockInfo], prev_workday: str, target_date: str
) -> list[ZtStockInfo]:
    """
    对涨停股票列表逐个检查所有规则，返回通过所有规则的股票列表。
    """
    result: list[ZtStockInfo] = []
    for stock in zt_list:
        if await check_stock_all_rules(stock, prev_workday, target_date):
            result.append(stock)
    logger.info("通过所有规则筛选的股票数量: %d 只", len(result))
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

        # Step 3-5: 检查所有股票是否满足所有规则（目标日未涨停跌停、规则4、规则5）
        # 每个股票内部会先查 DB，没有数据则调 API 获取并保存
        zt_list = await filter_stocks_by_all_rules(zt_list, prev_workday, target_date)
        if not zt_list:
            print(f"[INFO] {target_date} 规则筛选后无股票。")
            return

        # Step 6: 写入 stock_n 表
        inserted = await save_stock_n(zt_list, target_date, prev_workday)
        print(f"[INFO] {target_date} 入库完成：zt_stock {len(zt_list)} 条，stock_n {inserted} 条。")

    finally:
        logger.info(f"API 调用统计: get_zt_stock_list={ApiCallCounter.get_zt_stock_list_count()} 次, get_day_detail={ApiCallCounter.get_day_detail_count()} 次")
        await close_mysql_engine()


def main() -> None:
    args = _parse_args()
    target_date = _resolve_date(args.date)
    asyncio.run(_run(target_date))


if __name__ == "__main__":
    os.environ.get("MYSQL_DSN")
    main()
