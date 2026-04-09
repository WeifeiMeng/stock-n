import asyncio
import sys
from pathlib import Path
from src.dao import ZtStockDAO

# 直接运行时，将 backend 目录加入 path，以便导入 src
if __name__ == '__main__':
    _backend = Path(__file__).resolve().parent.parent.parent
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

from datetime import datetime, timedelta, timezone
import logging
import chinese_calendar
from typing import List
from src.stock_service.ztapi import get_day_detail, get_zt_stock_list
from src.stock_service.tools import get_market
from src.vo.stock import ZtStockInfo, DayStockInfo

logger = logging.getLogger(__name__)

# 涨停阈值：收盘价较前日涨幅 >= 9.5% 视为涨停（主板约10%，科创板/创业板约20%用更高阈值）
ZT_THRESHOLD = 1.10
# 跌停阈值
DT_THRESHOLD = 0.905
# 涨停涨幅百分比（与 ZT_THRESHOLD 一致）
ZT_PCT = (ZT_THRESHOLD - 1) * 100  # 9.5

def _get_prev_days(date: str, i: int) -> str:
    """获取 date 的前i个工作日（北京时间）"""
    date_obj = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=8)))
    prev_day = date_obj - timedelta(days=i)
    return prev_day.strftime('%Y-%m-%d')

def _get_prev_workday(date: str) -> str:
    """获取 date 的前一个工作日（北京时间，跳过节假日）"""
    date_obj = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=8)))
    prev_day = date_obj - timedelta(days=1)
    while not chinese_calendar.is_workday(prev_day.date()):
        prev_day = prev_day - timedelta(days=1)
    return prev_day.strftime('%Y-%m-%d')


# rule: 今日未涨停未跌停
# @param stock_list: 股票列表
# @param date: 日期 (当日)
# @return: 未涨停未跌停的股票列表
async def rule_for_today(stock_list: List[ZtStockInfo], previous_day: str, date: str) -> List[ZtStockInfo]:
    result_stock_list: List[ZtStockInfo] = []
    # 过滤出今日未涨停未跌停的股票
    previous_day_yyyymmdd = previous_day.replace('-', '')
    date_yyyymmdd = date.replace('-', '')
    logger.info(f"stock_list candidates: length {len(stock_list)}, detail: {stock_list}")
    for stock in stock_list:
        stock_day_info = await get_day_detail(previous_day_yyyymmdd, date_yyyymmdd, stock.code, stock.name)
        print(f"stock_day_info: {stock_day_info}")
        if len(stock_day_info) < 2:
            continue
        lastday_info, today_info = stock_day_info[0], stock_day_info[1]
        if lastday_info.end_pri <= 0:
            continue
        if (today_info.end_pri / lastday_info.end_pri >= ZT_THRESHOLD) or (today_info.end_pri / lastday_info.end_pri <= DT_THRESHOLD):
            continue
        else:
            result_stock_list.append(stock)
    
    logging.info(f"rule_for_today: {result_stock_list}")
    return result_stock_list


# 过滤 ST、*ST、北交所股票（保留沪深市场股票）
def rule_filter_st_bj(zt_list: List[ZtStockInfo]) -> List[ZtStockInfo]:
    result_stock_list: List[ZtStockInfo] = []
    for stock in zt_list:
        # 过滤 ST、*ST
        if stock.name.startswith('ST') or stock.name.startswith('*ST'):
            continue
        # 过滤北交所：8 开头、4 开头为北交所股票
        if stock.code.startswith('8') or stock.code.startswith('4'):
            continue
        # 过滤 get_market 无法识别的（可能含北交所等）
        if get_market(stock.code) is None:
            continue
        result_stock_list.append(stock)
    return result_stock_list

# rule: 涨停股票，且不是连续涨停的股票
def rule_zt(zt_list: List[ZtStockInfo]) -> List[ZtStockInfo]:
    """
    过滤出涨停股票：涨跌幅 zf >= 9.5% 视为涨停（与 ZT_THRESHOLD 一致）
    """
    return [stock for stock in zt_list if stock.zf >= ZT_PCT]


def _is_zt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断是否涨停：当日收盘价较前日涨幅 >= 9.5%"""
    if prev_end_pri <= 0 or curr_end_pri <= 0:
        return False
    rate = float((curr_end_pri + 0.01) / prev_end_pri) 
    return rate > ZT_THRESHOLD


def _is_dt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断是否跌停：当日收盘价较前日跌幅 >= 9.5%"""
    if prev_end_pri <= 0:
        return False
    if curr_end_pri <= 0:
        return True  # 价格归零视为跌停
    return curr_end_pri / prev_end_pri <= DT_THRESHOLD


# rule: 涨停前的七个交易日没有连续涨停，没有跌停
# zt_date: 涨停日
async def rule_no_zt_no_dt(zt_list: List[ZtStockInfo], zt_date: str) -> List[ZtStockInfo]:
    """过滤出涨停前 7 个交易日内无连续涨停、无跌停的股票"""
    zt_date_yyyymmdd = zt_date.replace('-', '')
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=20)
    start_date_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: List[ZtStockInfo] = []
    for stock in zt_list:
        day_list: List[DayStockInfo] = await get_day_detail(
            start_date_yyyymmdd, zt_date_yyyymmdd, stock.code, stock.name
        )
        # 至少需要 9 条：前一日 + 涨停前 7 个交易日（用于比较每日涨跌幅）
        if len(day_list) < 9:
            continue
        # day_list 按日期升序，[-9:-1] 为涨停日前 8 天（含前基准日），取其中后 7 天为「涨停前7个交易日」
        # 即 day_list[-8]..day_list[-2] 共 7 天
        has_dt = False
        consecutive_zt = 0
        for i in range(7):
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


# rule: 涨停前的30个交易日有过涨停
# zt_date: 涨停日
async def rule_zt_30_days(zt_list: List[ZtStockInfo], zt_date: str) -> List[ZtStockInfo]:
    """过滤出涨停前 30 个交易日内有过涨停的股票"""
    zt_date_yyyymmdd = zt_date.replace('-', '')
    start_date_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=60)
    start_date_yyyymmdd = start_date_obj.strftime('%Y%m%d')

    result: List[ZtStockInfo] = []
    for stock in zt_list:
        day_list: List[DayStockInfo] = await get_day_detail(
            start_date_yyyymmdd, zt_date_yyyymmdd, stock.code, stock.name
        )
        if len(day_list) < 2:
            continue
        # 取 zt_date 前最多 30 个交易日（不含 zt_date），即 day_list[-31:-1]
        pre_days = day_list[-31:-1] if len(day_list) > 31 else day_list[:-1]
        if len(pre_days) < 2:
            continue
        has_zt = False
        for i in range(1, min(len(pre_days), 31)):
            prev_pri = pre_days[i - 1].end_pri
            curr_pri = pre_days[i].end_pri
            if _is_zt(prev_pri, curr_pri):
                has_zt = True
                break
        if has_zt:
            result.append(stock)
    return result


async def single_stock_filter(stock: ZtStockInfo, date: str) -> bool:
    """判断单只股票是否满足：在 date 前一工作日（涨停日）前的 30 个交易日内有过涨停"""
    zt_date = _get_prev_workday(date)
    filtered = await rule_zt_30_days([stock], zt_date)
    return len(filtered) > 0


# 过滤规则：获取前一交易日涨停，今日未涨停未跌停，非 ST/*ST/北交所的股票
async def filter_zt_stocks(date: str) -> List[ZtStockInfo]:
    """
    过滤出符合以下条件的股票：
    1. 给定日期前一个交易日涨停
    2. 给定日期未涨停、未跌停
    3. 排除 ST、*ST、北交所股票

    @param date: 交易日期 (YYYY-MM-DD)
    @return: 符合条件的股票列表
    """
    prev_workday = _get_prev_workday(date)

    # 1. 获取前一交易日涨停的股票（从 API 获取）
    zt_list = await get_zt_stock_list(prev_workday)
    logger.info(f"filter_zt_stocks: 获取 {prev_workday} 涨停股票 %d 只", len(zt_list))

    # 2. 过滤 ST、*ST、北交所股票
    zt_list = rule_filter_st_bj(zt_list)
    logger.info(f"filter_zt_stocks: 过滤 ST/*ST/北交所后剩余 %d 只", len(zt_list))

    # 3. 过滤今日未涨停未跌停的股票
    zt_list = await rule_for_today(zt_list, prev_workday, date)
    logger.info(f"filter_zt_stocks: 过滤今日涨停/跌停后剩余 %d 只", len(zt_list))

    return zt_list


async def n_calculate_rule(date: str) -> List[ZtStockInfo]:
    """
    按日期执行完整的 N 规则筛选流程。

    规则链：
    1. 获取前一交易日涨停的股票
    2. 过滤 ST、*ST、北交所股票
    3. 过滤今日未涨停未跌停的股票
    4. 过滤涨停前 7 个交易日内有跌停或连续涨停的股票
    5. 过滤涨停前 30 个交易日内没有涨停过的股票
    """
    one_day_before = _get_prev_workday(date)

    # 1. 获取前一交易日涨停的股票
    zt_entities = await ZtStockDAO.list_by_trade_date(one_day_before)
    # DAO 返回 ZtStockEntity，转换为 ZtStockInfo 供规则函数使用
    zt_list = [
        ZtStockInfo(
            code=e.code,
            name=e.name,
            pri=e.pri,
            zf=e.zf,
            cje=e.cje,
            lt=e.lt,
            zsz=e.zsz,
            hs=e.hs,
            fbt=e.fbt,
            lbt=e.lbt,
            zj=e.zj,
            zbc=e.zbc,
            lbc=e.lbc,
            tj=e.tj,
        )
        for e in zt_entities
    ]
    logger.info(f"N 规则筛选：获取昨日涨停股票 %d 只", len(zt_list))

    # 2. 过滤 ST、*ST、北交所股票
    zt_list = rule_filter_st_bj(zt_list)
    logger.info(f"N 规则筛选：过滤 ST/*ST/北交所后剩余 %d 只", len(zt_list))

    # 3. 过滤今日未涨停未跌停的股票
    zt_list = await rule_for_today(zt_list, one_day_before, date)
    logger.info(f"N 规则筛选：过滤今日涨停/跌停后剩余 %d 只", len(zt_list))

    # 4. 过滤涨停前 7 个交易日有跌停或连续涨停的股票
    zt_list = await rule_no_zt_no_dt(zt_list, date)
    logger.info(f"N 规则筛选：过滤近 7 日有跌停/连续涨停后剩余 %d 只", len(zt_list))

    # 5. 过滤涨停前 30 个交易日内没有涨停过的股票
    zt_list = await rule_zt_30_days(zt_list, date)
    logger.info(f"N 规则筛选：过滤近 30 日无涨停后剩余 %d 只", len(zt_list))

    return zt_list


if __name__ == '__main__':
    asyncio.run(n_calculate_rule('2026-03-19'))
