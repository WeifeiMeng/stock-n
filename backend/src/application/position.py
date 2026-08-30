from dataclasses import dataclass
from math import ceil


MIN_BUY_AMOUNT = 5000.0
LOT_SIZE = 100
BUY_1_MULTIPLIER = 1.03
BUY_2_MULTIPLIER = 1.04
TAKE_PROFIT_MULTIPLIER = 1.05
STOP_LOSS_MULTIPLIER = 0.95


@dataclass(frozen=True)
class PositionPlan:
    buy_price: float
    buy_level: str
    triggered: bool
    lots: int
    shares: int
    amount: float


@dataclass(frozen=True)
class SellPlan:
    triggered: bool
    sell_price: float
    sell_amount: float
    profit_amount: float
    profit_rate: float
    profit_status: str
    exit_reason: str


def calculate_position_plan(base_price: float, lowest_price: float) -> PositionPlan:
    if base_price <= 0:
        return PositionPlan(
            buy_price=0.0,
            buy_level="",
            triggered=False,
            lots=0,
            shares=0,
            amount=0.0,
        )

    buy_level = "B1"
    buy_price = round(base_price * BUY_1_MULTIPLIER, 2)
    triggered = lowest_price > 0 and lowest_price <= buy_price
    if not triggered:
        buy_level = "B2"
        buy_price = round(base_price * BUY_2_MULTIPLIER, 2)
        triggered = lowest_price > 0 and lowest_price <= buy_price

    lots = max(1, ceil(MIN_BUY_AMOUNT / (LOT_SIZE * buy_price)))
    shares = lots * LOT_SIZE
    amount = round(shares * buy_price, 2)

    if not triggered:
        lots = 0
        shares = 0
        amount = 0.0

    return PositionPlan(
        buy_price=buy_price,
        buy_level=buy_level if triggered else "",
        triggered=triggered,
        lots=lots,
        shares=shares,
        amount=amount,
    )


def calculate_sell_plan(buy_price: float, shares: int, highest_price: float, lowest_price: float) -> SellPlan:
    if buy_price <= 0 or shares <= 0:
        return SellPlan(False, 0.0, 0.0, 0.0, 0.0, "", "")

    take_profit_price = round(buy_price * TAKE_PROFIT_MULTIPLIER, 2)
    stop_loss_price = round(buy_price * STOP_LOSS_MULTIPLIER, 2)

    sell_price = 0.0
    exit_reason = ""
    if lowest_price > 0 and lowest_price <= stop_loss_price:
        sell_price = stop_loss_price
        exit_reason = "stop_loss"
    elif highest_price > 0 and highest_price >= take_profit_price:
        sell_price = take_profit_price
        exit_reason = "take_profit"

    if sell_price <= 0:
        return SellPlan(False, 0.0, 0.0, 0.0, 0.0, "", "")

    buy_amount = round(shares * buy_price, 2)
    sell_amount = round(shares * sell_price, 2)
    profit_amount = round(sell_amount - buy_amount, 2)
    profit_rate = round(profit_amount / buy_amount * 100, 2) if buy_amount > 0 else 0.0
    profit_status = "profit" if profit_amount > 0 else "loss" if profit_amount < 0 else "even"
    return SellPlan(True, sell_price, sell_amount, profit_amount, profit_rate, profit_status, exit_reason)
