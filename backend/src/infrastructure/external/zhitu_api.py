"""智图API客户端，使用httpx异步请求，修复阻塞事件循环的bug (bug fix #6)"""
import asyncio
import logging
import os
import httpx
import pandas as pd
from typing import List

from src.domain.model import DayStockInfo, ZtStockInfo
from src.domain.rules import get_market

logger = logging.getLogger(__name__)

env_tokens = os.environ.get('ZT_API_TOKENS', '')
if env_tokens:
    TOKENS = [t.strip() for t in env_tokens.split(',') if t.strip()]
else:
    TOKENS = [
        'A7EB52CA-9651-4E41-8905-21AC0EA9F954',
        '46155FEF-7936-4034-A04D-8199E642EF1B',
        '62BE3028-01C1-4D86-9AF5-3E3F01A4CE9B',
    ]

_current_token_index = 0
_failed_tokens: set[int] = set()
REQUEST_INTERVAL = 0.3


def _get_current_token() -> str:
    return TOKENS[_current_token_index]


def _rotate_token() -> str:
    global _current_token_index
    for _ in range(len(TOKENS)):
        _current_token_index = (_current_token_index + 1) % len(TOKENS)
        if _current_token_index not in _failed_tokens:
            return TOKENS[_current_token_index]
    _failed_tokens.clear()
    return TOKENS[_current_token_index]


def _mark_token_failed() -> None:
    _failed_tokens.add(_current_token_index)


class ZhituApiClient:
    """智图API异步客户端"""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_zt_stock_list(self, date: str) -> List[ZtStockInfo]:
        client = await self._get_client()
        for attempt in range(len(TOKENS) + 1):
            token = _get_current_token()
            url = f'https://api.zhituapi.com/hs/pool/ztgc/{date}?token={token}'
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    _mark_token_failed()
                    _rotate_token()
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    result = []
                    for _, row in df.iterrows():
                        result.append(ZtStockInfo(
                            code=row['dm'], name=row['mc'], pri=row['p'],
                            zf=row['zf'], cje=row['cje'], lt=row['lt'],
                            zsz=row['zsz'], hs=row['hs'], fbt=row['fbt'],
                            lbt=row['lbt'], zj=row['zj'], zbc=row['zbc'],
                            lbc=row['lbc'], tj=row['tj'],
                        ))
                    _failed_tokens.clear()
                    return result
                elif isinstance(data, dict) and data.get('code') == -404:
                    _mark_token_failed()
                    _rotate_token()
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                else:
                    return []
            except httpx.HTTPError as e:
                logger.warning("API request failed %s: %s", url, e)
                _rotate_token()
                await asyncio.sleep(2 ** attempt * 0.5)
        _failed_tokens.clear()
        return []

    async def get_day_detail(self, start_date: str, end_date: str, code: str, name: str) -> List[DayStockInfo]:
        await asyncio.sleep(REQUEST_INTERVAL)
        client = await self._get_client()
        market = get_market(code)
        for attempt in range(len(TOKENS) + 1):
            token = _get_current_token()
            url = f"https://api.zhituapi.com/hs/history/{code}.{market}/d/n?token={token}&st={start_date}&et={end_date}&limit=30"
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    _mark_token_failed()
                    _rotate_token()
                    await asyncio.sleep(2 ** attempt * 0.5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    if 't' in df.columns:
                        df['t'] = pd.to_datetime(df['t'])
                    result = []
                    for _, row in df.iterrows():
                        result.append(DayStockInfo(
                            code=code, name=name, market=market or '', industry='',
                            start_pri=float(row['o']) if pd.notna(row['o']) else 0.0,
                            end_pri=float(row['c']) if pd.notna(row['c']) else 0.0,
                            highest_pri=float(row['h']) if pd.notna(row['h']) else 0.0,
                            lowest_pri=float(row['l']) if pd.notna(row['l']) else 0.0,
                            date=row['t'].strftime('%Y-%m-%d') if pd.notna(row['t']) else '',
                        ))
                    _failed_tokens.clear()
                    return result
                else:
                    return []
            except httpx.HTTPError as e:
                logger.warning("API request failed %s: %s", url, e)
                _rotate_token()
                await asyncio.sleep(2 ** attempt * 0.5)
        _failed_tokens.clear()
        return []
