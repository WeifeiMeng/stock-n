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
    rejected: list[str] = []


class StockNItem(BaseModel):
    code: str
    name: str
    current_price: float
    base_price: float
