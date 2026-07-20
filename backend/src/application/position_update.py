from dataclasses import dataclass

from src.domain.model import StockPositionInfo
from src.domain.rules import get_prev_workday

from .position import calculate_position_plan
from .protocols import DayDataProvider, StockRepository


@dataclass
class PositionUpdateResult:
    trade_date: str
    source_date: str
    source_total: int
    positions_inserted: int


async def update_positions_from_prev_stock_n(
    trade_date: str,
    provider: DayDataProvider,
    repo: StockRepository,
) -> PositionUpdateResult:
    source_date = get_prev_workday(trade_date)
    source_stocks = await repo.get_stock_n_list(source_date)

    await repo.delete_stock_positions_by_date(trade_date)
    if not source_stocks:
        return PositionUpdateResult(
            trade_date=trade_date,
            source_date=source_date,
            source_total=0,
            positions_inserted=0,
        )

    positions: list[StockPositionInfo] = []
    api_date = trade_date.replace("-", "")
    for stock in source_stocks:
        day_rows = await provider.get_day_data(
            stock.code,
            stock.name,
            api_date,
            api_date,
            min_records=1,
        )
        today_info = next((row for row in day_rows if row.date == trade_date), None)
        if today_info is None:
            continue

        plan = calculate_position_plan(stock.base_price, today_info.lowest_pri)
        if not plan.triggered:
            continue

        positions.append(StockPositionInfo(
            code=stock.code,
            name=stock.name,
            trade_date=trade_date,
            base_price=stock.base_price,
            highest_price=today_info.highest_pri,
            lowest_price=today_info.lowest_pri,
            buy_price=plan.buy_price,
            buy_lots=plan.lots,
            buy_shares=plan.shares,
            buy_amount=plan.amount,
        ))

    inserted = await repo.save_stock_positions_batch(positions)
    return PositionUpdateResult(
        trade_date=trade_date,
        source_date=source_date,
        source_total=len(source_stocks),
        positions_inserted=inserted,
    )
