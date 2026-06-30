from typing import List, NamedTuple


class BuyLevel(NamedTuple):
    level: str
    buy_price: float
    stop_loss_price: float


def calculate_stock_prices(current_price: float) -> List[BuyLevel]:
    multipliers = [("买一价", 1.04), ("买二价", 1.03), ("买三价", 1.02)]
    return [
        BuyLevel(
            level=label,
            buy_price=round(current_price * m, 2),
            stop_loss_price=round(current_price * m * 0.95, 2),
        )
        for label, m in multipliers
    ]
