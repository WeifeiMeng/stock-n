"""
板块/行业相关服务。
"""
from __future__ import annotations

from typing import List

# 涨停阈值：收盘价较前日涨幅 >= 9.5% 视为涨停
ZT_THRESHOLD = 1.095


def has_zt_in_last_n_days(day_list: List, target_date: str, n: int = 7) -> bool:
    """
    判断股票在 target_date 之前的前 n 个交易日内是否有过涨停。

    涨停判定：当日收盘价 / 前日收盘价 >= ZT_THRESHOLD（涨幅 >= 9.5%）

    Args:
        day_list: 按日期升序排列的日线列表（List[DayStockInfo]）
        target_date: 目标日期，格式 YYYY-MM-DD
        n: 往前回溯的交易天数，默认 7

    Returns:
        True = 前 n 个交易日内曾涨停，False = 没有涨停
    """
    if not day_list or len(day_list) < 2:
        return False

    # day_list 按日期升序，取最后 n+1 条（保证有 n 个对比对）
    recent = day_list[-(n + 1) :] if len(day_list) > n else day_list

    for i in range(1, len(recent)):
        prev_pri = recent[i - 1].end_pri
        curr_pri = recent[i].end_pri
        if prev_pri <= 0 or curr_pri <= 0:
            continue
        if curr_pri / prev_pri >= ZT_THRESHOLD:
            return True
    return False
