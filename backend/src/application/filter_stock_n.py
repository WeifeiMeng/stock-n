"""N规则筛选应用服务，合并 filter_stock_n.py + n_calculate.py，修复全部 bug"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List

from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo
from src.domain.rules import (
    is_zt, is_dt, filter_st_bj,
    ZT_THRESHOLD, DT_THRESHOLD, get_market,
    get_prev_workday, get_n_prev_workday,
)
from .protocols import DayDataProvider, ZtApiClient, StockRepository

logger = logging.getLogger(__name__)


@dataclass
class FilterResultItem:
    stock: ZtStockInfo
    passed: bool
    reason: str = ""


@dataclass
class PipelineResult:
    target_date: str
    prev_workday: str
    zt_total: int = 0
    passed: list[ZtStockInfo] = field(default_factory=list)
    rejected: list[FilterResultItem] = field(default_factory=list)
    stock_n_inserted: int = 0


async def _get_day_data_cached(
    code: str, name: str, start_date: str, end_date: str,
    provider: DayDataProvider, min_records: int = 2,
) -> list[DayStockInfo]:
    return await provider.get_day_data(code, name, start_date, end_date, min_records)


async def check_stock_all_rules(
    stock: ZtStockInfo,
    prev_workday: str,
    target_date: str,
    provider: DayDataProvider,
) -> FilterResultItem:
    """检查单只股票，返回通过/未通过+原因（bug fixes #1, #2, #3）"""
    prev_yy = prev_workday.replace('-', '')
    target_yy = target_date.replace('-', '')

    # ---- Step 3: 目标日未涨停未跌停 ----
    day_list_3 = await _get_day_data_cached(stock.code, stock.name, prev_yy, target_yy, provider)
    if len(day_list_3) < 2:
        return FilterResultItem(stock, False, "步骤3: 日线数据不足")
    # Bug fix #3: 按日期精确匹配而非索引
    prev_info = None
    today_info = None
    for d in day_list_3:
        if d.date == prev_workday:
            prev_info = d
        if d.date == target_date:
            today_info = d
    if prev_info is None or today_info is None:
        return FilterResultItem(stock, False, "步骤3: 日期数据缺失")
    if prev_info.end_pri <= 0:
        return FilterResultItem(stock, False, "步骤3: 前日收盘价<=0")
    ratio_3 = today_info.end_pri / prev_info.end_pri
    if ratio_3 >= ZT_THRESHOLD:
        return FilterResultItem(stock, False, f"步骤3: 目标日涨停({ratio_3:.4f} >= {ZT_THRESHOLD})")
    if ratio_3 <= DT_THRESHOLD:
        return FilterResultItem(stock, False, f"步骤3: 目标日跌停({ratio_3:.4f} <= {DT_THRESHOLD})")

    # ---- Rule 4: 涨停前7交易日无跌停、无连续涨停 ----
    rule4_start = get_n_prev_workday(target_date, 14)
    rule4_start_yy = rule4_start.replace('-', '')
    day_list_4 = await _get_day_data_cached(
        stock.code, stock.name, rule4_start_yy, target_yy, provider, min_records=10,
    )
    if len(day_list_4) < 10:
        return FilterResultItem(stock, False, f"规则4: 数据不足(需>=10, 实际{len(day_list_4)})")
    # Bug fix #2: [-10:-2] 不包含涨停日，正确取7个交易日前
    check_days = day_list_4[-10:-2]
    if len(check_days) != 8:
        return FilterResultItem(stock, False, f"规则4: 前7交易日数据不足(需8, 实际{len(check_days)})")

    consecutive_zt = 0
    for i in range(1, len(check_days)):
        prev_pri = check_days[i - 1].end_pri
        curr_pri = check_days[i].end_pri
        if prev_pri <= 0:
            continue
        if is_dt(prev_pri, curr_pri):
            return FilterResultItem(stock, False, f"规则4: 前7日跌停({check_days[i].date})")
        if is_zt(prev_pri, curr_pri):
            consecutive_zt += 1
            if consecutive_zt >= 2:
                return FilterResultItem(stock, False, f"规则4: 前7日连续涨停({check_days[i].date})")
        else:
            consecutive_zt = 0

    # ---- Rule 5: 涨停前30交易日有涨停记录 ----
    rule5_start = get_n_prev_workday(prev_workday, 35)
    rule5_start_yy = rule5_start.replace('-', '')
    day_list_5 = await _get_day_data_cached(stock.code, stock.name, rule5_start_yy, prev_yy, provider)
    if len(day_list_5) < 2:
        return FilterResultItem(stock, False, "规则5: 历史数据不足")
    # Bug fix #1: [-31:-1] instead of [-25:-2], [:-1] instead of [:-2]
    pre_days = day_list_5[-31:-1] if len(day_list_5) >= 31 else day_list_5[:-1]
    if len(pre_days) < 2:
        return FilterResultItem(stock, False, "规则5: 前30日数据不足")

    for i in range(1, len(pre_days)):
        if is_zt(pre_days[i - 1].end_pri, pre_days[i].end_pri):
            return FilterResultItem(stock, True, "")

    return FilterResultItem(stock, False, "规则5: 前30日无涨停记录")


async def filter_stocks_by_all_rules(
    zt_list: list[ZtStockInfo],
    prev_workday: str,
    target_date: str,
    provider: DayDataProvider,
) -> tuple[list[ZtStockInfo], list[FilterResultItem]]:
    passed: list[ZtStockInfo] = []
    rejected: list[FilterResultItem] = []
    for stock in zt_list:
        result = await check_stock_all_rules(stock, prev_workday, target_date, provider)
        if result.passed:
            passed.append(stock)
        else:
            rejected.append(result)
    logger.info("筛选结果: %d 只 → 通过 %d, 淘汰 %d", len(zt_list), len(passed), len(rejected))
    return passed, rejected


async def save_stock_n_batch(
    stocks: list[ZtStockInfo],
    target_date: str,
    prev_workday: str,
    provider: DayDataProvider,
    repo: StockRepository,
) -> int:
    """构造 StockNInfo 并保存"""
    base_date = get_n_prev_workday(target_date, 2)
    stock_n_list: list[StockNInfo] = []
    for stock in stocks:
        day_list = await _get_day_data_cached(stock.code, stock.name, base_date, target_date, provider)
        if len(day_list) < 2:
            continue
        base_info = None
        target_info = None
        zt_day_info = None
        for d in day_list:
            if d.date == base_date:
                base_info = d
            if d.date == target_date:
                target_info = d
            if d.date == prev_workday:
                zt_day_info = d
        if base_info is None or target_info is None or zt_day_info is None:
            continue
        stock_n_list.append(StockNInfo(
            code=stock.code, name=stock.name,
            market=get_market(stock.code) or "", industry="",
            start_pri=target_info.start_pri, end_pri=target_info.end_pri,
            highest_pri=target_info.highest_pri, lowest_pri=target_info.lowest_pri,
            date=target_date,
            zt=is_zt(zt_day_info.end_pri, target_info.end_pri),
            dt=is_dt(zt_day_info.end_pri, target_info.end_pri),
            n=stock.lbc, base_price=base_info.end_pri,
        ))
    if not stock_n_list:
        return 0
    return await repo.save_stock_n_batch(stock_n_list)


async def run_full_pipeline(
    target_date: str,
    api: ZtApiClient,
    provider: DayDataProvider,
    repo: StockRepository,
) -> PipelineResult:
    """完整 N 规则筛选流程"""
    prev_workday = get_prev_workday(target_date)
    result = PipelineResult(target_date=target_date, prev_workday=prev_workday)
    logger.info("N规则筛选: 目标日=%s, 涨停日=%s", target_date, prev_workday)

    # Step 1-2: 获取涨停股票，优先DB→API
    zt_stocks = await repo.get_zt_stocks(prev_workday)
    if not zt_stocks:
        zt_stocks = await api.get_zt_stock_list(prev_workday)
        if not zt_stocks:
            logger.info("无涨停数据")
            return result
        await repo.save_zt_stocks(zt_stocks, prev_workday)

    zt_stocks = filter_st_bj(zt_stocks)
    result.zt_total = len(zt_stocks)
    logger.info("涨停股票: %d 只(去ST/北交所后)", len(zt_stocks))

    # Step 3-5: 规则筛选
    passed, rejected = await filter_stocks_by_all_rules(zt_stocks, prev_workday, target_date, provider)
    result.passed = passed
    result.rejected = rejected

    # Step 6: 入库 stock_n
    if passed:
        result.stock_n_inserted = await save_stock_n_batch(passed, target_date, prev_workday, provider, repo)
        logger.info("入库 stock_n: %d 条", result.stock_n_inserted)

    return result
