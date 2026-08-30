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
    stock_positions_inserted: int = 0
    rejected: list[str] = []


class PositionUpdateResponse(BaseModel):
    success: bool
    date: str
    source_date: str
    source_total: int
    positions_inserted: int
    positions_sold: int = 0
    open_positions_checked: int = 0


class PositionItem(BaseModel):
    code: str
    name: str
    trade_date: str
    base_price: float
    highest_price: float
    lowest_price: float
    buy1_price: float
    buy_level: str = "B1"
    buy_lots: int
    buy_shares: int
    buy_amount: float
    sell_date: str = ""
    sell_price: float = 0.0
    sell_amount: float = 0.0
    profit_amount: float = 0.0
    profit_rate: float = 0.0
    profit_status: str = ""
    exit_reason: str = ""
    status: str


class StockNItem(BaseModel):
    code: str
    name: str
    current_price: float
    base_price: float
    highest_price: float
    lowest_price: float
    buy1_price: float
    position_triggered: bool
    buy_lots: int
    buy_shares: int
    buy_amount: float


class CalculateRequest(BaseModel):
    current_price: float = Field(..., gt=0)
