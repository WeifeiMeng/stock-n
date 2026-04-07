"""
API 路由定义
"""
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
    - **price**: 当前价格（昨日收盘价）
    - **buy_price**: 买入价格（前两交易日收盘 × 1.03）
    - **take_profit_price**: 止盈价格（买入价格 × 1.05）
    - **stop_loss_price**: 止损价格（买入价格 × 0.95）
    """
    try:
        entities = await StockNDAO.list_by_trade_date(date)
        if not entities:
            return []

        # 计算涨停日（前一交易日）
        zt_date = _get_prev_workday(date)
        zt_yyyymmdd = zt_date.replace('-', '')
        from datetime import datetime, timedelta
        start_obj = datetime.strptime(zt_date, '%Y-%m-%d') - timedelta(days=10)
        start_yyyymmdd = start_obj.strftime('%Y%m%d')

        result: list[StockNItem] = []
        session_factory = get_session_factory()

        for entity in entities:
            # 优先从 day_stock 表查询前两个交易日的数据
            ref_day = None
            async with session_factory() as session:
                # 找前两个交易日（涨停日的前两个交易日）
                ref_date_1 = _get_prev_workday(zt_date)
                ref_date_2 = _get_prev_workday(ref_date_1)
                ref_date = ref_date_2

                db_day = await DayStockDAO.get_by_code_and_date(session, entity.code, ref_date)
                if db_day:
                    ref_day = db_day

            # DB 没有则调接口
            if ref_day is None:
                day_list = await get_day_detail(start_yyyymmdd, zt_yyyymmdd, entity.code, entity.name)
                if len(day_list) < 3:
                    continue
                ref_day = day_list[-3]  # 前两个交易日
                if ref_day.end_pri <= 0:
                    continue

            buy_price = round(ref_day.end_pri * 1.03, 2)
            result.append(StockNItem(
                name=entity.name,
                price=entity.end_pri,
                buy_price=buy_price,
                take_profit_price=round(buy_price * 1.05, 2),
                stop_loss_price=round(buy_price * 0.95, 2),
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 stock_n 数据失败: {str(e)}")
