from datetime import datetime, timedelta, timezone
import logging
from typing import List
from src.stock_service.ztapi import get_day_detail, get_zt_stock_list
from src.stock_service.tools import get_market
from src.vo.stock import ZtStockInfo, DayStockInfo

# 涨停阈值：收盘价较前日涨幅 >= 9.5% 视为涨停（主板约10%，科创板/创业板约20%用更高阈值）
ZT_THRESHOLD = 1.095
# 跌停阈值
DT_THRESHOLD = 0.905


def _get_prev_workday(date: str) -> str:
    """获取 date 的前一个工作日（北京时间）"""
    date_obj = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=8)))
    weekday = date_obj.weekday()
    prev_day = date_obj - timedelta(days=3) if weekday == 0 else date_obj - timedelta(days=1)
    return prev_day.strftime('%Y-%m-%d')


# rule: 今日未涨停未跌停
# date: 2026-01-26
async def rule_for_today(date: str) -> List[ZtStockInfo]:
    target_date = _get_prev_workday(date)
    target_date_yyyymmdd = target_date.replace('-', '')
    date_yyyymmdd = date.replace('-', '')
    # 获取前一日的涨停股票
    stock_list = await get_zt_stock_list(target_date)

    result_stock_list: List[ZtStockInfo] = []
    # 过滤出今日未涨停未跌停的股票
    for stock in stock_list:
        stock_day_info = await get_day_detail(target_date_yyyymmdd, date_yyyymmdd, stock.code, stock.name)
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
    过滤出涨停股票
    """
    return [stock for stock in zt_list if stock.zf > 0]

def _is_zt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断是否涨停"""
    if prev_end_pri <= 0:
        return False
    return curr_end_pri / prev_end_pri >= ZT_THRESHOLD


def _is_dt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断是否跌停"""
    if prev_end_pri <= 0:
        return False
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


async def n_calculate_rule(date: str) -> List[ZtStockInfo]:
    target_date = _get_prev_workday(date)  # 涨停日
    zt_list = await rule_for_today(date)
    zt_list = rule_filter_st_bj(zt_list)
    zt_list = rule_zt(zt_list)
    zt_list = await rule_no_zt_no_dt(zt_list, target_date)
    zt_list = await rule_zt_30_days(zt_list, target_date)
    return zt_list


async def single_stock_filter(stock: ZtStockInfo, date: str) -> bool:
    """判断单只股票是否满足：在 date 前一工作日（涨停日）前的 30 个交易日内有过涨停"""
    zt_date = _get_prev_workday(date)
    filtered = await rule_zt_30_days([stock], zt_date)
    return len(filtered) > 0