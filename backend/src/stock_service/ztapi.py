# https://www.zhituapi.com/hsstockapi.html
import asyncio
import logging
import os
import sys
import time
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

# 支持多个API Key，按顺序轮换使用
# 优先从环境变量读取，支持逗号分隔的多个key
env_tokens = os.environ.get('ZT_API_TOKENS', '')
if env_tokens:
    TOKENS = [t.strip() for t in env_tokens.split(',') if t.strip()]
else:
    TOKENS = [
        'A7EB52CA-9651-4E41-8905-21AC0EA9F954',
        '46155FEF-7936-4034-A04D-8199E642EF1B',
        '62BE3028-01C1-4D86-9AF5-3E3F01A4CE9B',
    ]

# 当前使用的token索引
_current_token_index = 0

# 失败的key索引集合（用于暂时跳过失败的key）
_failed_tokens = set()


def get_current_token() -> str:
    """获取当前使用的API token"""
    return TOKENS[_current_token_index]


def rotate_token() -> str:
    """轮换到下一个可用的token并返回"""
    global _current_token_index
    
    # 找到下一个未失败的token
    for i in range(len(TOKENS)):
        _current_token_index = (_current_token_index + 1) % len(TOKENS)
        if _current_token_index not in _failed_tokens:
            logger.info(f"已切换到第 {_current_token_index + 1} 个API Key")
            return TOKENS[_current_token_index]
    
    # 如果所有token都失败了，重置失败状态并返回第一个
    reset_failed_tokens()
    logger.info("所有API Key均已重试，重置失败状态")
    return TOKENS[_current_token_index]


def mark_token_failed():
    """标记当前token失败"""
    global _failed_tokens
    _failed_tokens.add(_current_token_index)
    logger.warning(f"标记第 {_current_token_index + 1} 个API Key为失败")


def reset_failed_tokens():
    """重置所有失败的token状态"""
    global _failed_tokens
    _failed_tokens = set()
    logger.info("已重置所有API Key失败状态")


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
    for attempt in range(len(TOKENS) + 1):
        token = get_current_token()
        url = f'https://api.zhituapi.com/hs/pool/ztgc/{date}?token={token}'
        
        try:
            response = requests.get(url, timeout=30)
            data = _parse_json(response, url)
            
            if data is not None:
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
                    reset_failed_tokens()  # 成功后重置失败状态
                    return stock_info_list
                elif isinstance(data, dict) and data.get('code') == -404:
                    # 数据未更新，标记为失败但继续尝试
                    mark_token_failed()
                else:
                    # 空数据或其他情况
                    return []
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求异常: {e}")
        
        # 如果当前token失败，轮换到下一个
        if attempt < len(TOKENS):
            logger.warning(f"第 {attempt + 1} 个API Key请求失败，尝试下一个")
            rotate_token()
            # 指数退避等待
            await asyncio.sleep(2 ** attempt * 0.5)
    
    logger.warning("所有API Key均请求失败")
    reset_failed_tokens()
    return []


# 获取股票日线数据
# @start_date: 开始日期
# @end_date: 结束日期
# @code: 股票代码
# @name: 股票名称
# @return: 股票日线数据列表
# API 请求间隔（秒），避免限流
REQUEST_INTERVAL = 0.3


async def get_day_detail(start_date: str, end_date: str, code: str, name: str) -> List[DayStockInfo]:
    await asyncio.sleep(REQUEST_INTERVAL)  # 请求间隔，避免 API 限流
    
    for attempt in range(len(TOKENS) + 1):
        token = get_current_token()
        market = get_market(code)
        url = f"https://api.zhituapi.com/hs/history/{code}.{market}/d/n?token={token}&st={start_date}&et={end_date}&limit=30"
        
        try:
            response = requests.get(url, timeout=30)
            data = _parse_json(response, url)
            
            if data is not None:
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
                            name=name,
                            market=market or '',
                            industry='',
                            start_pri=float(row['o']) if pd.notna(row['o']) else 0.0,
                            end_pri=float(row['c']) if pd.notna(row['c']) else 0.0,
                            highest_pri=float(row['h']) if pd.notna(row['h']) else 0.0,
                            lowest_pri=float(row['l']) if pd.notna(row['l']) else 0.0,
                            date=row['t'].strftime('%Y-%m-%d') if pd.notna(row['t']) else ''
                        )
                        stock_info_list.append(stock_info)
                    
                    reset_failed_tokens()  # 成功后重置失败状态
                    return stock_info_list
                else:
                    return []  # 返回空列表
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求异常: {e}")
        
        # 如果当前token失败，轮换到下一个
        if attempt < len(TOKENS):
            logger.warning(f"第 {attempt + 1} 个API Key请求失败，尝试下一个")
            rotate_token()
            # 指数退避等待
            await asyncio.sleep(2 ** attempt * 0.5)
    
    logger.warning("所有API Key均请求失败")
    reset_failed_tokens()
    return []

if __name__ == '__main__':
    date = '2026-03-19'
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    start_date = date_obj - timedelta(days=32)
    start_date_str = start_date.strftime('%Y-%m-%d')
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