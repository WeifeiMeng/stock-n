"""
API 数据模型
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import List


class CalculateRequest(BaseModel):
    """计算请求模型（按日期）"""
    date: str = Field(..., description="日期，格式 YYYY-MM-DD，如 2026-02-04")


class StockPriceRequest(BaseModel):
    """股票价格计算请求模型"""
    current_price: float = Field(..., gt=0, description="当前股票价格，必须大于0")


class BuyLevel(BaseModel):
    """买入价位信息"""
    level: str = Field(..., description="价位名称，如'买一价'")
    buy_price: float = Field(..., description="买入价格")
    stop_loss_price: float = Field(..., description="止损价格")
    stop_loss_percentage: float = Field(..., description="止损幅度百分比")


class StockPriceResponse(BaseModel):
    """股票价格计算响应模型"""
    current_price: float = Field(..., description="输入的当前价格")
    buy_levels: List[BuyLevel] = Field(..., description="各买入价位信息")


class ZtStockInfoResponse(BaseModel):
    """涨停股票信息（API 响应）"""
    model_config = ConfigDict(from_attributes=True)

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


class StockNItem(BaseModel):
    """stock_n 列表项"""
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格（昨日收盘价）")
    buy_price: float = Field(..., description="买入价格（前两交易日收盘 × 1.03）")
    take_profit_price: float = Field(..., description="止盈价格（买入价格 × 1.05）")
    stop_loss_price: float = Field(..., description="止损价格（买入价格 × 0.95）")
