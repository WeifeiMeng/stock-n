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


@dataclass
class StockPositionInfo:
    code: str
    name: str
    trade_date: str
    base_price: float
    highest_price: float
    lowest_price: float
    buy_price: float
    buy_lots: int
    buy_shares: int
    buy_amount: float
    status: str = "holding"
