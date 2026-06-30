"""N规则筛选应用服务，合并 filter_stock_n.py + n_calculate.py，修复全部 bug"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import List, AsyncGenerator

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

    # ---- Rule 4: 涨停前7交易日规则（无跌停、无连续涨停、至少有另一个涨停） ----
    rule4_start = get_n_prev_workday(target_date, 14)
    rule4_start_yy = rule4_start.replace('-', '')
    day_list_4 = await _get_day_data_cached(
        stock.code, stock.name, rule4_start_yy, target_yy, provider, min_records=10,
    )
    if len(day_list_4) < 10:
        return FilterResultItem(stock, False, f"规则4: 数据不足(需>=10, 实际{len(day_list_4)})")
    # check_days: [0]=8天前基准, [1]~[7]=前7交易日, [8]=涨停日
    check_days = day_list_4[-10:-1]
    if len(check_days) != 9:
        return FilterResultItem(stock, False, f"规则4: 前7交易日数据不足(需9, 实际{len(check_days)})")

    consecutive_zt = 0
    has_zt = False  # 窗口内是否有涨停（不含涨停日自身）
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
            # i == len-1 是涨停日本身，不计入窗口内涨停
            if i < len(check_days) - 1:
                has_zt = True
        else:
            consecutive_zt = 0

    if not has_zt:
        return FilterResultItem(stock, False, "规则4: 前7日无涨停记录")

    return FilterResultItem(stock, True, "")


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
    # 先删除该日期已有数据，再插入新结果
    await repo.delete_stock_n_by_date(target_date)
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
    if zt_stocks:
        # DB 数据已在保存时过滤过，无需再过滤
        result.zt_total = len(zt_stocks)
    else:
        zt_stocks = await api.get_zt_stock_list(prev_workday)
        if not zt_stocks:
            logger.info("无涨停数据")
            return result
        # 过滤后保存到 DB
        zt_stocks = filter_st_bj(zt_stocks)
        result.zt_total = len(zt_stocks)
        if zt_stocks:
            await repo.save_zt_stocks(zt_stocks, prev_workday)
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


def _sse_event(event_type: str, data: dict) -> str:
    """将 dict 格式化为 SSE 事件字符串"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def run_full_pipeline_stream(
    target_date: str,
    api: ZtApiClient,
    provider: DayDataProvider,
    repo: StockRepository,
) -> AsyncGenerator[str, None]:
    """完整 N 规则筛选流程（SSE 流式版本），逐只推送进度事件"""
    prev_workday = get_prev_workday(target_date)
    logger.info("N规则筛选(SSE): 目标日=%s, 涨停日=%s", target_date, prev_workday)

    # Step 1-2: 获取涨停股票
    zt_stocks = await repo.get_zt_stocks(prev_workday)
    if zt_stocks:
        zt_total = len(zt_stocks)
    else:
        zt_stocks = await api.get_zt_stock_list(prev_workday)
        if not zt_stocks:
            yield _sse_event("complete", {
                "type": "complete", "success": True,
                "date": target_date, "prev_workday": prev_workday,
                "zt_total": 0, "passed_count": 0, "rejected_count": 0,
                "stock_n_inserted": 0, "rejected": [],
            })
            return
        zt_stocks = filter_st_bj(zt_stocks)
        zt_total = len(zt_stocks)
        if zt_stocks:
            await repo.save_zt_stocks(zt_stocks, prev_workday)
        logger.info("涨停股票: %d 只(去ST/北交所后)", zt_total)

    # Step 3-5: 逐只检查并推送进度
    passed_list: list[ZtStockInfo] = []
    rejected_list: list[FilterResultItem] = []
    total = len(zt_stocks)

    for idx, stock in enumerate(zt_stocks):
        result = await check_stock_all_rules(stock, prev_workday, target_date, provider)
        if result.passed:
            passed_list.append(stock)
        else:
            rejected_list.append(result)

        yield _sse_event("progress", {
            "type": "progress",
            "current": idx + 1,
            "total": total,
            "passed": len(passed_list),
            "rejected": len(rejected_list),
            "stock": {
                "code": stock.code,
                "name": stock.name,
                "passed": result.passed,
                "reason": result.reason if not result.passed else "",
            },
        })

    logger.info("筛选结果: %d 只 → 通过 %d, 淘汰 %d", total, len(passed_list), len(rejected_list))

    # Step 6: 入库
    stock_n_inserted = 0
    if passed_list:
        stock_n_inserted = await save_stock_n_batch(passed_list, target_date, prev_workday, provider, repo)
        logger.info("入库 stock_n: %d 条", stock_n_inserted)

    yield _sse_event("complete", {
        "type": "complete", "success": True,
        "date": target_date, "prev_workday": prev_workday,
        "zt_total": zt_total,
        "passed_count": len(passed_list),
        "rejected_count": len(rejected_list),
        "stock_n_inserted": stock_n_inserted,
        "rejected": [
            f"{r.stock.name}({r.stock.code}): {r.reason}"
            for r in rejected_list
        ],
    })
