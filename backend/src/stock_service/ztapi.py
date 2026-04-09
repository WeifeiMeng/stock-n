# https://www.zhituapi.com/hsstockapi.html
import asyncio
import logging
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# 处理导入路径，支持直接运行和作为模块导入
try:
    from ..vo.stock import DayStockInfo, ZtStockInfo
    from .tools import get_market
except ImportError:
    # 直接运行时，添加项目根目录到路径
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.vo.stock import DayStockInfo, ZtStockInfo
    from src.stock_service.tools import get_market

token = 'A7EB52CA-9651-4E41-8905-21AC0EA9F954'


def _parse_json(response: requests.Response, url: str) -> Optional[Any]:
    """安全解析 JSON，失败时记录日志并返回 None"""
    try:
        # 单独检查 429 状态码，抛出更明确的异常
        if response.status_code == 429:
            raise requests.exceptions.HTTPError("API Rate Limited", response=response)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.warning("API 请求失败 %s: %s, body: %s", url, e, response.text[:200])
        return None
    except requests.exceptions.JSONDecodeError as e:
        logger.warning("JSON 解析失败 %s: %s, body: %s", url, e, response.text[:200])
        return None


# 获取涨停股票列表
async def get_zt_stock_list(date: str) -> List[ZtStockInfo]:
    url = f'https://api.zhituapi.com/hs/pool/ztgc/{date}?token={token}'
    response = requests.get(url)
    data = _parse_json(response, url)
    if data is None:
        logger.warning("get_zt_stock_list API 请求失败 %s", url)
        return []

    if isinstance(data, list) and len(data) > 0:
        df = pd.DataFrame(data)
        stock_info_list = []
        for _, row in df.iterrows():
            stock_info = ZtStockInfo(
                code=row['dm'],
                name=row['mc'],
                pri=row['p'],
                zf=row['zf'],
                cje=row['cje'],
                lt=row['lt'],
                zsz=row['zsz'],
                hs=row['hs'],
                fbt=row['fbt'],
                lbt=row['lbt'],
                zj=row['zj'],
                zbc=row['zbc'],
                lbc=row['lbc'],
                tj=row['tj'],
            )
            stock_info_list.append(stock_info)
        return stock_info_list
    logger.warning("get_zt_stock_list JSON 解析失败 %s", url)
    return []


# 获取股票日线数据
# @start_date: 开始日期
# @end_date: 结束日期
# @code: 股票代码
# @name: 股票名称
# @return: 股票日线数据列表
# API 请求间隔（秒），避免限流
REQUEST_INTERVAL = 0.5


async def get_day_detail(start_date: str, end_date: str, code: str, name: str) -> List[DayStockInfo]:
    await asyncio.sleep(REQUEST_INTERVAL)  # 请求间隔，避免 API 限流
    market = get_market(code)
    url = f"https://api.zhituapi.com/hs/history/{code}.{market}/d/n?token={token}&st={start_date}&et={end_date}&limit=30"
    response = requests.get(url)
    data = _parse_json(response, url)
    if data is None:
        return []
    
    # 将数据转换为pandas DataFrame
    if isinstance(data, list) and len(data) > 0:
        df = pd.DataFrame(data)
        # 将时间列转换为datetime类型
        if 't' in df.columns:
            df['t'] = pd.to_datetime(df['t'])
        
        # 将DataFrame转换为DayStockInfo对象列表
        stock_info_list = []
        for _, row in df.iterrows():
            stock_info = DayStockInfo(
                code=code,
                name=name,  # API数据中没有股票名称，设为空字符串
                market=market or '',  # 市场代码
                industry='',  # API数据中没有行业信息，设为空字符串
                start_pri=float(row['o']) if pd.notna(row['o']) else 0.0,  # 开盘价
                end_pri=float(row['c']) if pd.notna(row['c']) else 0.0,  # 收盘价
                highest_pri=float(row['h']) if pd.notna(row['h']) else 0.0,  # 最高价
                lowest_pri=float(row['l']) if pd.notna(row['l']) else 0.0,  # 最低价
                date=row['t'].strftime('%Y-%m-%d') if pd.notna(row['t']) else ''  # 日期转换为字符串
            )
            stock_info_list.append(stock_info)
        
        return stock_info_list
    else:
        return []  # 返回空列表

if __name__ == '__main__':
    date = '2026-03-19'
    # 将字符串转换为datetime对象
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    # 计算32天前的日期
    start_date = date_obj - timedelta(days=32)
    # 将结果转换回字符串格式（YYYY-MM-DD）
    start_date_str = start_date.strftime('%Y-%m-%d')
    # 转换为YYYYMMDD格式
    date_yyyymmdd = date.replace('-', '')
    start_date_yyyymmdd = start_date.strftime('%Y%m%d')
    
    print(f'原始日期: {date}')
    print(f'32天前的日期: {start_date_str}')
    print(f'32天前的日期(YYYYMMDD): {start_date_yyyymmdd}')
    print(f'原始日期(YYYYMMDD): {date_yyyymmdd}')
    
    zt_list = asyncio.run(get_zt_stock_list(date))
    print(f'\n涨停股票数据条数: {len(zt_list)}')
    if zt_list:
        print(f'\n前3条数据:')
        for i, info in enumerate(zt_list[:3]):
            print(f'{i+1}. {info}')
    stock_info_list = asyncio.run(get_day_detail(start_date_yyyymmdd, date_yyyymmdd, '000670', name='格力电器'))
    print(f'\n数据条数: {len(stock_info_list)}')
    if stock_info_list:
        print(f'\n前3条数据:')
        for i, info in enumerate(stock_info_list[:3]):
            print(f'{i+1}. {info}')