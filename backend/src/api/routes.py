"""
API 路由定义
"""
import sys
import asyncio
from pathlib import Path

from fastapi import HTTPException

from src.service import n_calculate
from src.dao import StockNDAO, DayStockDAO
from src.service.n_calculate import _get_prev_workday
from src.stock_service.ztapi import get_day_detail
from src.middleware import get_session_factory
from .models import CalculateRequest, ZtStockInfoResponse, StockNItem


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


async def get_stock_n_list(date: str) -> list[StockNItem]:
    """
    获取指定日期的 stock_n 列表，包含买卖价格信息。

    - **date**: 日期，格式 YYYY-MM-DD
    - **name**: 股票名称
    - **current_price**: 当前价格（昨日收盘价）
    - **base_price**: 基础价格（前两交易日收盘价）
    """
    try:
        entities = await StockNDAO.list_by_trade_date(date)
        if not entities:
            return []

        result: list[StockNItem] = []
        for entity in entities:
            base_price = entity.base_price
            if base_price <= 0:
                continue

            result.append(StockNItem(
                code=entity.code,
                name=entity.name,
                current_price=entity.end_pri,
                base_price=base_price,
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 stock_n 数据失败: {str(e)}")


async def run_filter_stock_n(date: str):
    """
    执行 filter_stock_n.py 筛选脚本。

    - **date**: 日期，格式 YYYY-MM-DD
    """
    backend_root = Path(__file__).resolve().parent.parent.parent
    script_path = backend_root / "scripts" / "filter_stock_n.py"

    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在: {script_path}")

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script_path), "--date", date,
        cwd=str(backend_root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(status_code=504, detail="脚本执行超时")
