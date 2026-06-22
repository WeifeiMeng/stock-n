# Backend DDD Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor backend from script-based monolithic structure to DDD layered architecture (domain/application/infrastructure/presentation), fixing 8 bugs and eliminating code duplication.

**Architecture:** Four-layer DDD: domain (pure logic), application (orchestration via protocols), infrastructure (DB/API implementations), presentation (FastAPI). Application depends only on domain + protocols; infrastructure implements protocols.

**Tech Stack:** Python 3.13+, FastAPI, SQLAlchemy 2.0 async, httpx (new), aiomysql, chinese-calendar

---

## File Structure Map

```
backend/src/                           # NEW STRUCTURE
├── domain/
│   ├── __init__.py
│   ├── model.py                       # DayStockInfo, ZtStockInfo, StockNInfo
│   └── rules.py                       # Pure functions + constants
├── application/
│   ├── __init__.py
│   ├── protocols.py                   # DayDataProvider, ZtApiClient, StockRepository (typing.Protocol)
│   ├── filter_stock_n.py              # Merged filter pipeline
│   └── price_calculate.py            # From api/services.py
├── infrastructure/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py                    # Single DeclarativeBase
│   │   ├── connection.py              # Engine, session factory, Depends helper
│   │   ├── entities.py               # All ORM entities
│   │   └── repositories.py           # DAO → Repository implementations
│   ├── external/
│   │   ├── __init__.py
│   │   └── zhitu_api.py              # httpx async client
├── presentation/
│   ├── __init__.py
│   ├── app.py                        # FastAPI instance, CORS, lifecycle
│   ├── routes.py                     # Route registration
│   ├── deps.py                       # FastAPI Depends
│   └── models.py                     # Pydantic request/response
└── scripts/                          # (unchanged location)
    └── test_filter_rules.py          # Updated imports
```

---

### Task 1: Create domain layer

**Files:**
- Create: `backend/src/domain/__init__.py`
- Create: `backend/src/domain/model.py`
- Create: `backend/src/domain/rules.py`

- [ ] **Step 1: Copy model.py from vo/stock.py**

`backend/src/domain/model.py`:
```python
from dataclasses import dataclass

@dataclass
class DayStockInfo:
    code: str
    name: str
    market: str
    industry: str
    start_pri: float
    end_pri: float
    highest_pri: float
    lowest_pri: float
    date: str

@dataclass
class ZtStockInfo:
    code: str
    name: str
    pri: float
    zf: float
    cje: float
    lt: float
    zsz: float
    hs: float
    fbt: str
    lbt: str
    zj: float
    zbc: int
    lbc: int
    tj: str

@dataclass
class StockNInfo:
    code: str
    name: str
    market: str
    industry: str
    start_pri: float
    end_pri: float
    highest_pri: float
    lowest_pri: float
    date: str
    zt: bool
    dt: bool
    n: int
    base_price: float
```

- [ ] **Step 2: Create rules.py with pure functions, constants, calendar helpers (bug fixes #4, #5, #8)**

`backend/src/domain/rules.py`:
```python
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
```

- [ ] **Step 3: Create `__init__.py`**

`backend/src/domain/__init__.py` — empty.

- [ ] **Step 4: Verify domain layer has no external dependencies**

Run: `cd backend && uv run python -c "from src.domain.model import DayStockInfo, ZtStockInfo, StockNInfo; from src.domain.rules import is_zt, is_dt, get_prev_workday, get_n_prev_workday, filter_st_bj; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/src/domain/ backend/src/vo/
git commit -m "feat: add domain layer with pure model and rules, fix is_zt/is_dt bugs"
```

---

### Task 2: Create infrastructure database layer

**Files:**
- Create: `backend/src/infrastructure/__init__.py`
- Create: `backend/src/infrastructure/database/__init__.py`
- Create: `backend/src/infrastructure/database/base.py`
- Create: `backend/src/infrastructure/database/entities.py`
- Create: `backend/src/infrastructure/database/connection.py`
- Create: `backend/src/infrastructure/database/repositories.py`

- [ ] **Step 1: Create base.py — single DeclarativeBase (bug fix #7)**

`backend/src/infrastructure/database/base.py`:
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2: Create entities.py — all ORM entities in one file**

`backend/src/infrastructure/database/entities.py`:
```python
from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class ZtStockEntity(Base):
    __tablename__ = "zt_stock"
    __table_args__ = (Index("idx_zt_stock_code_trade_date", "code", "trade_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zf: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cje: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lt: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zsz: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fbt: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    lbt: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    zj: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zbc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lbc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tj: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")


class DayStockEntity(Base):
    __tablename__ = "day_stock"
    __table_args__ = (Index("idx_day_stock_code_date", "code", "trade_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    market: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    start_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    end_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    highest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lowest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")


class StockNEntity(Base):
    __tablename__ = "stock_n"
    __table_args__ = (
        Index("idx_stock_n_code_date", "code", "trade_date"),
        Index("idx_stock_n_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    market: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    start_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    end_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    highest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lowest_pri: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    zt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    base_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
```

- [ ] **Step 3: Create connection.py — extract from middleware/mysql.py**

`backend/src/infrastructure/database/connection.py`:
```python
from __future__ import annotations
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_mysql_dsn() -> str | None:
    dsn = os.getenv("MYSQL_DSN")
    if dsn:
        return dsn
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "123456")
    database = os.getenv("MYSQL_DATABASE", "stocks")
    if not all([host, user, password, database]):
        return None
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"


def _init_mysql_engine() -> None:
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return
    dsn = _build_mysql_dsn()
    if not dsn:
        return
    _engine = create_async_engine(
        dsn,
        connect_args={"server_public_key": True},
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    _session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    _init_mysql_engine()
    return _session_factory


def get_mysql_engine() -> AsyncEngine | None:
    _init_mysql_engine()
    return _engine


async def close_mysql_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends session provider."""
    sf = get_session_factory()
    if sf is None:
        raise RuntimeError("MySQL not configured")
    session = sf()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

- [ ] **Step 4: Create repositories.py — refactored from DAOs**

`backend/src/infrastructure/database/repositories.py`:
```python
from __future__ import annotations
from typing import Iterable, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo
from .entities import ZtStockEntity, DayStockEntity, StockNEntity


class ZtStockRepository:
    @staticmethod
    async def list_by_trade_date(session: AsyncSession, trade_date: str, limit: int = 200) -> List[ZtStockEntity]:
        stmt = (
            select(ZtStockEntity)
            .where(ZtStockEntity.trade_date == trade_date)
            .order_by(ZtStockEntity.zf.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[ZtStockInfo], trade_date: str) -> int:
        entities = [
            ZtStockEntity(
                code=s.code, name=s.name, pri=s.pri, zf=s.zf, cje=s.cje,
                lt=s.lt, zsz=s.zsz, hs=s.hs, fbt=s.fbt, lbt=s.lbt,
                zj=s.zj, zbc=s.zbc, lbc=s.lbc, tj=s.tj, trade_date=trade_date,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


class DayStockRepository:
    @staticmethod
    async def list_by_codes_and_date_range(
        session: AsyncSession, codes: list[str], start_date: str, end_date: str
    ) -> List[DayStockEntity]:
        stmt = (
            select(DayStockEntity)
            .where(
                DayStockEntity.code.in_(codes),
                DayStockEntity.trade_date >= start_date,
                DayStockEntity.trade_date <= end_date,
            )
            .order_by(DayStockEntity.trade_date)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        seen: set[tuple[str, str]] = set()
        deduped: list[DayStockEntity] = []
        for row in rows:
            key = (row.code, row.trade_date)
            if key not in seen:
                seen.add(key)
                deduped.append(row)
        return deduped

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[DayStockInfo]) -> int:
        entities = [
            DayStockEntity(
                code=s.code, name=s.name, market=s.market, industry=s.industry,
                start_pri=s.start_pri, end_pri=s.end_pri,
                highest_pri=s.highest_pri, lowest_pri=s.lowest_pri,
                trade_date=s.date,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


class StockNRepository:
    @staticmethod
    async def list_by_trade_date(session: AsyncSession, trade_date: str, limit: int = 200) -> List[StockNEntity]:
        stmt = (
            select(StockNEntity)
            .where(StockNEntity.trade_date == trade_date)
            .order_by(StockNEntity.n.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        seen: set[str] = set()
        deduped: list[StockNEntity] = []
        for row in rows:
            if row.code not in seen:
                seen.add(row.code)
                deduped.append(row)
        return deduped

    @staticmethod
    async def insert_many(session: AsyncSession, stocks: Iterable[StockNInfo]) -> int:
        entities = [
            StockNEntity(
                code=s.code, name=s.name, market=s.market, industry=s.industry,
                start_pri=s.start_pri, end_pri=s.end_pri,
                highest_pri=s.highest_pri, lowest_pri=s.lowest_pri,
                trade_date=s.date, zt=s.zt, dt=s.dt, n=s.n, base_price=s.base_price,
            )
            for s in stocks
        ]
        if not entities:
            return 0
        session.add_all(entities)
        await session.flush()
        return len(entities)


async def init_all_tables() -> None:
    from .connection import get_mysql_engine
    engine = get_mysql_engine()
    if engine is None:
        return
    from .entities import ZtStockEntity, DayStockEntity, StockNEntity
    from .base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[
            ZtStockEntity.__table__,
            DayStockEntity.__table__,
            StockNEntity.__table__,
        ])
```

- [ ] **Step 5: Create `__init__.py` files**

`backend/src/infrastructure/__init__.py` — empty.
`backend/src/infrastructure/database/__init__.py` — empty.

- [ ] **Step 6: Verify database layer**

Run: `cd backend && uv run python -c "from src.infrastructure.database.connection import get_session_factory; from src.infrastructure.database.repositories import init_all_tables, ZtStockRepository; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/src/infrastructure/
git commit -m "feat: add infrastructure database layer with unified Base and Repository pattern"
```

---

### Task 3: Create infrastructure external

**Files:**
- Create: `backend/src/infrastructure/external/__init__.py`
- Create: `backend/src/infrastructure/external/zhitu_api.py`

- [ ] **Step 1: Create zhitu_api.py with httpx (bug fix #6)**

`backend/src/infrastructure/external/zhitu_api.py`:
```python
"""智图API客户端，使用httpx异步请求"""
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
```

- [ ] **Step 2: Verify external layer**

Run: `cd backend && uv run python -c "from src.infrastructure.external.zhitu_api import ZhituApiClient; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/src/infrastructure/external/
git commit -m "feat: add async httpx API client"
```

---

### Task 4: Create application protocols and services

**Files:**
- Create: `backend/src/application/__init__.py`
- Create: `backend/src/application/protocols.py`
- Create: `backend/src/application/filter_stock_n.py`
- Create: `backend/src/application/price_calculate.py`

- [ ] **Step 1: Create protocols.py**

`backend/src/application/protocols.py`:
```python
from typing import Protocol, List
from src.domain.model import DayStockInfo, ZtStockInfo, StockNInfo


class DayDataProvider(Protocol):
    """日线数据获取协议"""
    async def get_day_data(
        self, code: str, name: str, start_date: str, end_date: str, min_records: int = 2
    ) -> List[DayStockInfo]: ...


class ZtApiClient(Protocol):
    """涨停API客户端协议"""
    async def get_zt_stock_list(self, date: str) -> List[ZtStockInfo]: ...


class StockRepository(Protocol):
    """股票数据仓库协议"""
    async def get_zt_stocks(self, trade_date: str) -> List[ZtStockInfo]: ...
    async def save_zt_stocks(self, stocks: List[ZtStockInfo], trade_date: str) -> int: ...
    async def save_stock_n_batch(self, stocks: List[StockNInfo]) -> int: ...
    async def get_stock_n_list(self, trade_date: str) -> List[StockNInfo]: ...
```

- [ ] **Step 2: Create price_calculate.py**

`backend/src/application/price_calculate.py`:
```python
from typing import List, NamedTuple


class BuyLevel(NamedTuple):
    level: str
    buy_price: float
    stop_loss_price: float


def calculate_stock_prices(current_price: float) -> List[BuyLevel]:
    multipliers = [("买一价", 1.04), ("买二价", 1.03), ("买三价", 1.02)]
    return [
        BuyLevel(
            level=label,
            buy_price=round(current_price * m, 2),
            stop_loss_price=round(current_price * m * 0.95, 2),
        )
        for label, m in multipliers
    ]
```

- [ ] **Step 3: Create filter_stock_n.py — merged pipeline with all bug fixes**

`backend/src/application/filter_stock_n.py`:
```python
"""N规则筛选应用服务，合并 filter_stock_n.py + n_calculate.py，修复全部 bug"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List

from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo
from src.domain.rules import is_zt, is_dt, filter_st_bj, ZT_THRESHOLD, DT_THRESHOLD, get_market, get_prev_workday, get_n_prev_workday
from .protocols import DayDataProvider, ZtApiClient, StockRepository

logger = logging.getLogger(__name__)


@dataclass
class FilterResultItem:
    stock: ZtStockInfo
    passed: bool
    reason: str = ""  # 淘汰原因


@dataclass
class PipelineResult:
    target_date: str
    prev_workday: str
    zt_total: int = 0
    passed: List[ZtStockInfo] = field(default_factory=list)
    rejected: List[FilterResultItem] = field(default_factory=list)
    stock_n_inserted: int = 0


async def _get_day_data_cached(
    code: str, name: str, start_date: str, end_date: str,
    provider: DayDataProvider, min_records: int = 2,
) -> List[DayStockInfo]:
    """获取日线数据，内部不直接调 DAO，通过 provider"""
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
    # Bug fix #2: [-10:-2] 不包含涨停日
    check_days = day_list_4[-10:-2]
    if len(check_days) != 8:
        return FilterResultItem(stock, False, f"规则4: 前7交易日数据不足(需8, 实际{len(check_days)})")

    has_dt = False
    consecutive_zt = 0
    for i in range(1, len(check_days)):
        prev_pri = check_days[i - 1].end_pri
        curr_pri = check_days[i].end_pri
        if prev_pri <= 0:
            continue
        if is_dt(prev_pri, curr_pri):
            has_dt = True
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

    has_zt = False
    for i in range(1, len(pre_days)):
        if is_zt(pre_days[i - 1].end_pri, pre_days[i].end_pri):
            has_zt = True
            break
    if not has_zt:
        return FilterResultItem(stock, False, "规则5: 前30日无涨停记录")

    return FilterResultItem(stock, True, "")


async def filter_stocks_by_all_rules(
    zt_list: List[ZtStockInfo],
    prev_workday: str,
    target_date: str,
    provider: DayDataProvider,
) -> tuple[List[ZtStockInfo], List[FilterResultItem]]:
    passed: List[ZtStockInfo] = []
    rejected: List[FilterResultItem] = []
    for stock in zt_list:
        result = await check_stock_all_rules(stock, prev_workday, target_date, provider)
        if result.passed:
            passed.append(stock)
        else:
            rejected.append(result)
    logger.info("筛选结果: %d 只 → 通过 %d, 淘汰 %d", len(zt_list), len(passed), len(rejected))
    return passed, rejected


async def save_stock_n_batch(
    stocks: List[ZtStockInfo],
    target_date: str,
    prev_workday: str,
    provider: DayDataProvider,
    repo: StockRepository,
) -> int:
    """构造 StockNInfo 并保存"""
    base_date = get_n_prev_workday(target_date, 2)
    stock_n_list: List[StockNInfo] = []
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
            code=stock.code, name=stock.name, market=get_market(stock.code) or "", industry="",
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
```

- [ ] **Step 4: Verify application layer**

Run: `cd backend && uv run python -c "from src.application.protocols import DayDataProvider, ZtApiClient, StockRepository; from src.application.filter_stock_n import run_full_pipeline, PipelineResult; from src.application.price_calculate import calculate_stock_prices; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/src/application/
git commit -m "feat: add application layer with merged filter pipeline and bug fixes"
```

---

### Task 5: Create presentation layer

**Files:**
- Create: `backend/src/presentation/__init__.py`
- Create: `backend/src/presentation/models.py`
- Create: `backend/src/presentation/deps.py`
- Create: `backend/src/presentation/routes.py`
- Create: `backend/src/presentation/app.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create presentation models.py**

`backend/src/presentation/models.py`:
```python
from pydantic import BaseModel, Field


class FilterRequest(BaseModel):
    date: str = Field(..., description="目标日期 YYYY-MM-DD")


class FilterResponse(BaseModel):
    success: bool
    date: str
    prev_workday: str
    zt_total: int
    passed_count: int
    rejected_count: int
    stock_n_inserted: int
    rejected: list[str] = []  # 淘汰原因列表: "股票名(代码): 原因"


class StockNItem(BaseModel):
    code: str
    name: str
    current_price: float
    base_price: float
```

- [ ] **Step 2: Create deps.py**

`backend/src/presentation/deps.py`:
```python
from typing import AsyncGenerator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db_session
from src.infrastructure.database.repositories import ZtStockRepository, DayStockRepository, StockNRepository
from src.infrastructure.external.zhitu_api import ZhituApiClient
from src.application.protocols import DayDataProvider, ZtApiClient, StockRepository
from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """获取 DB session（通过 Depends 注入）"""
    async for session in get_db_session():
        yield session


class _DefaultProviders:
    """基于基础设施实现的默认 Provider 适配器"""

    @staticmethod
    async def _zt_entity_to_info(e) -> ZtStockInfo:
        from src.infrastructure.database.entities import ZtStockEntity
        return ZtStockInfo(
            code=e.code, name=e.name, pri=e.pri, zf=e.zf, cje=e.cje,
            lt=e.lt, zsz=e.zsz, hs=e.hs, fbt=e.fbt, lbt=e.lbt,
            zj=e.zj, zbc=e.zbc, lbc=e.lbc, tj=e.tj,
        ) if isinstance(e, ZtStockEntity) else e

    @staticmethod
    async def _day_entity_to_info(e) -> DayStockInfo:
        return DayStockInfo(
            code=e.code, name=e.name or "", market=e.market or "",
            industry=e.industry or "", start_pri=e.start_pri, end_pri=e.end_pri,
            highest_pri=e.highest_pri, lowest_pri=e.lowest_pri, date=e.trade_date,
        )


def get_day_data_provider() -> DayDataProvider:
    class _Provider:
        async def get_day_data(self, code: str, name: str, start_date: str, end_date: str, min_records: int = 2):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.database.repositories import DayStockRepository
            from src.infrastructure.external.zhitu_api import ZhituApiClient
            sf = get_session_factory()
            if sf is None:
                return []
            async with sf() as session:
                entities = await DayStockRepository.list_by_codes_and_date_range(
                    session, [code], start_date, end_date
                )
            infos = [await _DefaultProviders._day_entity_to_info(e) for e in entities]
            if len(infos) >= min_records:
                return infos
            client = ZhituApiClient()
            try:
                api_days = await client.get_day_detail(start_date, end_date, code, name)
            finally:
                await client.close()
            if not api_days:
                return infos
            sf2 = get_session_factory()
            if sf2:
                async with sf2() as session:
                    await DayStockRepository.insert_many(session, api_days)
                    await session.commit()
            return api_days
    return _Provider()


def get_api_client() -> ZtApiClient:
    return ZhituApiClient()


def get_stock_repository() -> StockRepository:
    class _Repo:
        async def get_zt_stocks(self, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.database.repositories import ZtStockRepository
            sf = get_session_factory()
            if sf is None:
                return []
            async with sf() as session:
                entities = await ZtStockRepository.list_by_trade_date(session, trade_date)
            return [await _DefaultProviders._zt_entity_to_info(e) for e in entities]

        async def save_zt_stocks(self, stocks, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.database.repositories import ZtStockRepository
            sf = get_session_factory()
            if sf is None:
                return 0
            async with sf() as session:
                count = await ZtStockRepository.insert_many(session, stocks, trade_date)
                await session.commit()
            return count

        async def save_stock_n_batch(self, stocks):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.database.repositories import StockNRepository
            sf = get_session_factory()
            if sf is None:
                return 0
            async with sf() as session:
                count = await StockNRepository.insert_many(session, stocks)
                await session.commit()
            return count

        async def get_stock_n_list(self, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.database.repositories import StockNRepository
            sf = get_session_factory()
            if sf is None:
                return []
            async with sf() as session:
                entities = await StockNRepository.list_by_trade_date(session, trade_date)
            return [
                StockNInfo(
                    code=e.code, name=e.name, market=e.market, industry=e.industry,
                    start_pri=e.start_pri, end_pri=e.end_pri,
                    highest_pri=e.highest_pri, lowest_pri=e.lowest_pri,
                    date=e.trade_date, zt=e.zt, dt=e.dt, n=e.n, base_price=e.base_price,
                )
                for e in entities
            ]
    return _Repo()
```

- [ ] **Step 3: Create routes.py**

`backend/src/presentation/routes.py`:
```python
from fastapi import Depends, HTTPException

from src.application.filter_stock_n import run_full_pipeline
from src.application.price_calculate import calculate_stock_prices
from src.infrastructure.database.repositories import StockNRepository
from src.domain.rules import get_market
from .models import FilterRequest, FilterResponse, StockNItem
from .deps import get_day_data_provider, get_api_client, get_stock_repository, get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def root():
    return {"message": "股票价格计算API", "version": "2.0.0"}


async def health_check():
    return {"status": "healthy"}


async def run_filter(request: FilterRequest) -> FilterResponse:
    """执行 N 规则筛选（替代原 subprocess + /calculate）"""
    provider = get_day_data_provider()
    api = get_api_client()
    repo = get_stock_repository()
    try:
        result = await run_full_pipeline(request.date, api, provider, repo)
        return FilterResponse(
            success=True,
            date=result.target_date,
            prev_workday=result.prev_workday,
            zt_total=result.zt_total,
            passed_count=len(result.passed),
            rejected_count=len(result.rejected),
            stock_n_inserted=result.stock_n_inserted,
            rejected=[
                f"{r.stock.name}({r.stock.code}): {r.reason}"
                for r in result.rejected
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if hasattr(api, 'close'):
            await api.close()


async def get_stock_n_list(date: str) -> list[StockNItem]:
    """获取 stock_n 列表"""
    repo = get_stock_repository()
    try:
        entities = await repo.get_stock_n_list(date)
        return [
            StockNItem(
                code=e.code,
                name=e.name,
                current_price=e.end_pri,
                base_price=e.base_price,
            )
            for e in entities if e.base_price > 0
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def calculate_price(current_price: float):
    """简单价格计算"""
    levels = calculate_stock_prices(current_price)
    return {
        "current_price": current_price,
        "levels": [
            {"level": l.level, "buy_price": l.buy_price, "stop_loss_price": l.stop_loss_price}
            for l in levels
        ],
    }
```

- [ ] **Step 4: Create app.py**

`backend/src/presentation/app.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import root, health_check, run_filter, get_stock_n_list, calculate_price
from .models import FilterRequest, FilterResponse, StockNItem
from src.infrastructure.database.repositories import init_all_tables
from src.infrastructure.database.connection import close_mysql_engine

app = FastAPI(
    title="股票价格计算API",
    description="N规则筛选 + 价格计算",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Note: MySQLSessionMiddleware 已移除，改用路由级 Depends


@app.on_event("startup")
async def startup():
    await init_all_tables()


@app.on_event("shutdown")
async def shutdown():
    await close_mysql_engine()


app.get("/")(root)
app.get("/health")(health_check)
app.post("/stock-n/filter", response_model=FilterResponse)(run_filter)
app.get("/stock-n/{date}", response_model=list[StockNItem])(get_stock_n_list)
app.get("/calculate-price")(calculate_price)
```

- [ ] **Step 5: Update main.py**

`backend/main.py`:
```python
from pathlib import Path
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(BACKEND_ROOT / ".env", override=False)
load_dotenv(BACKEND_ROOT / ".env.local", override=True)

import uvicorn
from src.presentation.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 6: Verify presentation layer imports**

Run: `cd backend && uv run python -c "from src.presentation.app import app; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/src/presentation/ backend/main.py
git commit -m "feat: add presentation layer with new /stock-n/filter endpoint"
```

---

### Task 6: Update test script and frontend

**Files:**
- Modify: `backend/scripts/test_filter_rules.py`
- Modify: `frontend/stock-n.html`

- [ ] **Step 1: Update test_filter_rules.py imports**

Change from:
```python
from src.dao.zt_stock_dao import ZtStockDAO
from src.middleware import close_mysql_engine, get_session_factory
from src.stock_service.ztapi import get_zt_stock_list
from scripts.filter_stock_n import check_stock_all_rules, filter_stocks_by_all_rules
```

To:
```python
from src.infrastructure.database.repositories import ZtStockRepository
from src.infrastructure.database.connection import close_mysql_engine, get_session_factory
from src.infrastructure.external.zhitu_api import ZhituApiClient
from src.application.filter_stock_n import check_stock_all_rules, filter_stocks_by_all_rules
```

And adapt function bodies to use new APIs (get_zt_stock_list → api.get_zt_stock_list(date), repo methods instead of DAO methods).

- [ ] **Step 2: Update frontend stock-n.html**

Change API endpoint from `/stock-n/run-filter/{date}` to `/stock-n/filter` (POST with JSON body).

Find the init button fetch and update:
```javascript
// Old: fetch(`/stock-n/run-filter/${date}`, { method: 'POST' })
// New:
fetch('/stock-n/filter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date: date }),
})
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/test_filter_rules.py frontend/stock-n.html
git commit -m "fix: update test script and frontend for new API endpoints"
```

---

### Task 7: Remove old files and add httpx dependency

**Files:**
- Delete: `backend/src/api/` (entire directory)
- Delete: `backend/src/service/` (entire directory)
- Delete: `backend/src/stock_service/` (entire directory)
- Delete: `backend/src/vo/` (entire directory)
- Delete: `backend/src/middleware/` (entire directory)
- Delete: `backend/src/dao/` (entire directory)
- Delete: `backend/scripts/filter_stock_n.py`
- Modify: `backend/pyproject.toml` (add httpx)

- [ ] **Step 1: Add httpx dependency**

Edit `backend/pyproject.toml`, add `"httpx>=0.27.0"` to dependencies list.

- [ ] **Step 2: Install new dependency**

Run: `cd backend && uv sync`
Expected: httpx installed without errors

- [ ] **Step 3: Remove old source directories**

Delete the following directories and files (using file manager or shell):
```
backend/src/api/          (entire directory)
backend/src/service/      (entire directory)
backend/src/stock_service/(entire directory)
backend/src/vo/           (entire directory)
backend/src/middleware/   (entire directory)
backend/src/dao/          (entire directory)
backend/scripts/filter_stock_n.py
```

- [ ] **Step 4: Verify server starts**

Run: `cd backend && timeout 5 uv run python main.py || true`
Expected: No import errors, server starts clean.

- [ ] **Step 5: Commit**

```bash
git add -A backend/src/ backend/scripts/ backend/pyproject.toml backend/uv.lock backend/main.py frontend/
git commit -m "refactor: remove old module structure, add httpx, finalize DDD migration"
```

---

### Task 8: End-to-end verification

- [ ] **Step 1: Verify all imports resolve**

Run: `cd backend && uv run python -c "
from src.domain.model import DayStockInfo, ZtStockInfo, StockNInfo
from src.domain.rules import is_zt, is_dt, filter_st_bj, ZT_THRESHOLD, DT_THRESHOLD, get_market
from src.application.protocols import DayDataProvider, ZtApiClient, StockRepository
from src.application.filter_stock_n import run_full_pipeline, check_stock_all_rules
from src.application.price_calculate import calculate_stock_prices
from src.infrastructure.database.connection import get_session_factory, close_mysql_engine
from src.infrastructure.database.repositories import init_all_tables, ZtStockRepository, DayStockRepository, StockNRepository
from src.infrastructure.external.zhitu_api import ZhituApiClient
from src.presentation.app import app
from src.presentation.models import FilterRequest, FilterResponse, StockNItem
print('All imports OK')
"`

Expected: `All imports OK`

- [ ] **Step 2: Run domain unit tests (pure functions)**

Run: `cd backend && uv run python -c "
from src.domain.rules import is_zt, is_dt, filter_st_bj, ZT_THRESHOLD, get_market, ZtStockInfo
# Test is_zt
assert is_zt(10.0, 10.96) == True, '10→10.96 should be zt'
assert is_zt(10.0, 10.90) == False, '10→10.90 should not be zt'
assert is_zt(0, 10.0) == False, 'zero prev should not be zt'
# Test is_dt
assert is_dt(10.0, 9.00) == True, '10→9.00 should be dt'
assert is_dt(10.0, 9.50) == False, '10→9.50 should not be dt'
assert is_dt(10.0, 0) == True, 'zero curr should be dt'
# Test get_market
assert get_market('600123') == 'SH'
assert get_market('000001') == 'SZ'
assert get_market('8xxxxx') == None
print('All domain tests pass')
"`

Expected: `All domain tests pass`

- [ ] **Step 3: Verify server health endpoint**

Start server: `cd backend && uv run python main.py &`
Wait 2 seconds.
Run: `curl http://localhost:8000/health`
Expected: `{"status":"healthy"}`
Kill server.

- [ ] **Step 4: Verify GET /stock-n/{date} with known date**

Run: `curl http://localhost:8000/stock-n/2026-06-20`
Expected: 200 with JSON array (may be empty if no data).

- [ ] **Step 5: Commit if any fixes needed**

If verification passed without changes, no new commit needed.

---

### Task 9: Final cleanup and verification

- [ ] **Step 1: Check git status is clean**

Run: `git status`
Expected: Only intentional files changed, no leftover old files.

- [ ] **Step 2: Remove log files from tracking if needed**

Check: `git ls-files backend/log/`
If log files are tracked, add to gitignore.

- [ ] **Step 3: Final commit for any stragglers**

```bash
git add -A
git diff --cached --stat
git commit -m "chore: final cleanup after DDD refactoring"
```
