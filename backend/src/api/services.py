"""
API 业务逻辑服务
"""
from typing import List
from .models import BuyLevel


def calculate_stock_prices(current_price: float) -> List[BuyLevel]:
    """
    计算股票买一价、买二价、买三价及其对应的止损价

    Args:
        current_price: 当前股票价格

    Returns:
        List[BuyLevel]: 买入价位信息列表
    """
    buy_levels = []

    # 买一价：当前价格的1.04倍
    buy_price_1 = current_price * 1.04
    stop_loss_1 = buy_price_1 * 0.95
    stop_loss_percentage_1 = (1 - stop_loss_1 / buy_price_1) * 100

    buy_levels.append(BuyLevel(
        level="买一价",
        buy_price=round(buy_price_1, 2),
        stop_loss_price=round(stop_loss_1, 2),
        stop_loss_percentage=round(stop_loss_percentage_1, 1)
    ))

    # 买二价：当前价格的1.03倍
    buy_price_2 = current_price * 1.03
    stop_loss_2 = buy_price_2 * 0.95
    stop_loss_percentage_2 = (1 - stop_loss_2 / buy_price_2) * 100

    buy_levels.append(BuyLevel(
        level="买二价",
        buy_price=round(buy_price_2, 2),
        stop_loss_price=round(stop_loss_2, 2),
        stop_loss_percentage=round(stop_loss_percentage_2, 1)
    ))

    # 买三价：当前价格的1.02倍
    buy_price_3 = current_price * 1.02
    stop_loss_3 = buy_price_3 * 0.95
    stop_loss_percentage_3 = (1 - stop_loss_3 / buy_price_3) * 100

    buy_levels.append(BuyLevel(
        level="买三价",
        buy_price=round(buy_price_3, 2),
        stop_loss_price=round(stop_loss_3, 2),
        stop_loss_percentage=round(stop_loss_percentage_3, 1)
    ))

    return buy_levels
