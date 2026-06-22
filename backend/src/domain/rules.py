from __future__ import annotations
from datetime import datetime, timedelta, timezone
import chinese_calendar

# Bug fix #4: ZT_THRESHOLD changed from 1.096 to 1.095 (true 9.5%), removed +0.01 hack
ZT_THRESHOLD = 1.095
DT_THRESHOLD = 0.905
ZT_PCT = 9.5

MARKET_MAP = {
    '600': 'SH', '601': 'SH', '603': 'SH', '605': 'SH',
    '000': 'SZ', '001': 'SZ',
    '688': 'IB',
    '300': 'SZ', '301': 'SZ',
    '002': 'SZ',
}


# ---- calendar helpers (bug fix #8: unified UTC+8 tzinfo) ----

def get_prev_workday(date: str) -> str:
    """获取 date 的前一个工作日（UTC+8，跳过节假日）"""
    dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=8)))
    prev = dt - timedelta(days=1)
    while not chinese_calendar.is_workday(prev.date()):
        prev = prev - timedelta(days=1)
    return prev.strftime('%Y-%m-%d')


def get_n_prev_workday(date: str, n: int) -> str:
    """获取 date 的前 n 个工作日（UTC+8，跳过节假日）"""
    dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=8)))
    prev = dt - timedelta(days=1)
    count = 0
    while count < n:
        if chinese_calendar.is_workday(prev.date()):
            count += 1
            if count == n:
                break
        prev = prev - timedelta(days=1)
    return prev.strftime('%Y-%m-%d')


# ---- market helper ----

def get_market(code: str) -> str | None:
    return MARKET_MAP.get(code[:3])


# ---- 涨停/跌停判断 (bug fixes #4, #5) ----

def is_zt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断当日收盘价较前日涨幅 >= 9.5%（对称实现，无 +0.01 补偿）"""
    if prev_end_pri <= 0 or curr_end_pri <= 0:
        return False
    return (curr_end_pri / prev_end_pri) >= ZT_THRESHOLD


def is_dt(prev_end_pri: float, curr_end_pri: float) -> bool:
    """判断当日收盘价较前日跌幅 >= 9.5%（显式化 curr<=0 检查，与 is_zt 对称）"""
    if prev_end_pri <= 0:
        return False
    if curr_end_pri <= 0:
        return True
    return (curr_end_pri / prev_end_pri) <= DT_THRESHOLD


# ---- filter helpers ----

def filter_st_bj(stocks: list) -> list:
    """过滤 ST/*ST/北交所股票"""
    result = []
    for s in stocks:
        if s.name.startswith('ST') or s.name.startswith('*ST'):
            continue
        if s.code.startswith('8') or s.code.startswith('4'):
            continue
        if get_market(s.code) is None:
            continue
        result.append(s)
    return result
