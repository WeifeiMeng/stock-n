"""
API 路由定义
"""
from fastapi import HTTPException

from src.service import n_calculate
from .models import CalculateRequest, ZtStockInfoResponse


async def root():
    """API根路径"""
    return {"message": "股票价格计算API", "version": "1.0.0"}


async def calculate_prices(request: CalculateRequest):
    """
    按日期计算（N 规则筛选）

    - **date**: 日期，格式 YYYY-MM-DD，如 2026-02-04
    """
    try:
        result = await n_calculate.n_calculate_rule(request.date)
        return [ZtStockInfoResponse.model_validate(s) for s in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算过程中发生错误: {str(e)}")

async def calculate_n_prices(date: str):
    return await n_calculate.n_calculate_rule(date)

async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}
