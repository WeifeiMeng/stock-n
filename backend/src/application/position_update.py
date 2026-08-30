from dataclasses import dataclass

from src.domain.model import StockPositionInfo
from src.domain.rules import get_prev_workday

from .position import calculate_position_plan, calculate_sell_plan
from .protocols import DayDataProvider, StockRepository


@dataclass
class PositionUpdateResult:
    trade_date: str
    source_date: str
    source_total: int
    positions_inserted: int
    positions_sold: int = 0
    open_positions_checked: int = 0


async def update_positions_from_prev_stock_n(
    trade_date: str,
    provider: DayDataProvider,
    repo: StockRepository,
) -> PositionUpdateResult:
    source_date = get_prev_workday(trade_date)
    source_stocks = await repo.get_stock_n_list(source_date)
    open_positions = await repo.get_open_stock_positions_before(trade_date)
    open_codes_before_update = {position.code for position in open_positions}
    positions_sold = await update_open_positions(trade_date, open_positions, provider, repo)

    await repo.delete_stock_positions_by_date(trade_date)
    if not source_stocks:
        return PositionUpdateResult(
            trade_date=trade_date,
            source_date=source_date,
            source_total=0,
            positions_inserted=0,
            positions_sold=positions_sold,
            open_positions_checked=len(open_positions),
        )

    positions: list[StockPositionInfo] = []
    api_date = trade_date.replace("-", "")
    for stock in source_stocks:
        if stock.code in open_codes_before_update:
            continue

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
            buy_level=plan.buy_level,
        ))

    inserted = await repo.save_stock_positions_batch(positions)
    return PositionUpdateResult(
        trade_date=trade_date,
        source_date=source_date,
        source_total=len(source_stocks),
        positions_inserted=inserted,
        positions_sold=positions_sold,
        open_positions_checked=len(open_positions),
    )


async def update_open_positions(
    trade_date: str,
    open_positions: list[StockPositionInfo],
    provider: DayDataProvider,
    repo: StockRepository,
) -> int:
    sold_count = 0
    api_date = trade_date.replace("-", "")
    for position in open_positions:
        day_rows = await provider.get_day_data(
            position.code,
            position.name,
            api_date,
            api_date,
            min_records=1,
        )
        today_info = next((row for row in day_rows if row.date == trade_date), None)
        if today_info is None:
            continue

        sell_plan = calculate_sell_plan(
            position.buy_price,
            position.buy_shares,
            today_info.highest_pri,
            today_info.lowest_pri,
        )
        if not sell_plan.triggered:
            continue

        sold = StockPositionInfo(
            code=position.code,
            name=position.name,
            trade_date=position.trade_date,
            base_price=position.base_price,
            highest_price=position.highest_price,
            lowest_price=position.lowest_price,
            buy_price=position.buy_price,
            buy_lots=position.buy_lots,
            buy_shares=position.buy_shares,
            buy_amount=position.buy_amount,
            buy_level=position.buy_level,
            sell_date=trade_date,
            sell_price=sell_plan.sell_price,
            sell_amount=sell_plan.sell_amount,
            profit_amount=sell_plan.profit_amount,
            profit_rate=sell_plan.profit_rate,
            profit_status=sell_plan.profit_status,
            exit_reason=sell_plan.exit_reason,
            status="closed",
        )
        sold_count += await repo.close_stock_position(sold)
    return sold_count
