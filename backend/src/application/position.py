from dataclasses import dataclass
from math import ceil


MIN_BUY_AMOUNT = 5000.0
LOT_SIZE = 100
BUY_1_MULTIPLIER = 1.03


@dataclass(frozen=True)
class PositionPlan:
    buy_price: float
    triggered: bool
    lots: int
    shares: int
    amount: float


def calculate_position_plan(base_price: float, lowest_price: float) -> PositionPlan:
    if base_price <= 0:
        return PositionPlan(
            buy_price=0.0,
            triggered=False,
            lots=0,
            shares=0,
            amount=0.0,
        )

    buy_price = round(base_price * BUY_1_MULTIPLIER, 2)
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
        triggered=triggered,
        lots=lots,
        shares=shares,
        amount=amount,
    )
