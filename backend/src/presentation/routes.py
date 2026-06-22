from fastapi import HTTPException

from src.application.filter_stock_n import run_full_pipeline
from src.application.price_calculate import calculate_stock_prices
from .models import FilterRequest, FilterResponse, StockNItem
from .deps import get_day_data_provider, get_api_client, get_stock_repository


async def root():
    return {"message": "股票价格计算API", "version": "2.0.0"}


async def health_check():
    return {"status": "healthy"}


async def run_filter(request: FilterRequest) -> FilterResponse:
    """执行 N 规则筛选"""
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
