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
    zf: float # 涨跌幅 %
    cje: float # 成交额 元
    lt: float # 流通市值 元
    zsz: float # 总市值
    hs: float # 换手率
    fbt: str # 最初封板时间
    lbt: str # 最后封板时间
    zj: float # 封板资金
    zbc: int # 炸板次数
    lbc: int # 连板次数
    tj: str #涨停统计

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