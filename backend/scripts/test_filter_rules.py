"""
测试 check_stock_all_rules 和 filter_stocks_by_all_rules

用法:
    cd backend
    uv run python scripts/test_filter_rules.py --date 2026-03-25 --stock-code 000001
"""
import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.vo.stock import ZtStockInfo
from src.dao.zt_stock_dao import ZtStockDAO
from src.middleware import close_mysql_engine, get_session_factory
from src.stock_service.ztapi import get_zt_stock_list
from scripts.filter_stock_n import check_stock_all_rules, filter_stocks_by_all_rules


def get_prev_workday(date_str: str) -> str:
    """获取指定日期的前一个交易日（简单版本，仅工作日）"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    while True:
        dt -= timedelta(days=1)
        if dt.weekday() < 5:
            return dt.strftime("%Y-%m-%d")


async def get_stock_from_db(code: str, trade_date: str) -> ZtStockInfo | None:
    """从 zt_stock 表获取指定交易日、指定股票的涨停信息"""
    session_factory = get_session_factory()
    if session_factory is None:
        return None
    async with session_factory() as session:
        stocks = await ZtStockDAO.list_by_trade_date(session, trade_date, limit=500)
        for s in stocks:
            if s.code == code:
                return ZtStockInfo(
                    code=s.code,
                    name=s.name,
                    pri=s.pri,
                    zf=s.zf,
                    cje=s.cje,
                    lt=s.lt,
                    zsz=s.zsz,
                    hs=s.hs,
                    fbt=s.fbt,
                    lbt=s.lbt,
                    zj=s.zj,
                    zbc=s.zbc,
                    lbc=s.lbc,
                    tj=s.tj,
                )
        return None


async def get_stock_from_api(code: str, trade_date: str) -> ZtStockInfo | None:
    """从下游接口获取指定交易日、指定股票的涨停信息"""
    stocks = await get_zt_stock_list(trade_date)
    for s in stocks:
        if s.code == code:
            return s
    return None


async def get_stock(code: str, trade_date: str) -> ZtStockInfo | None:
    """
    获取股票涨停数据：
    1. 优先从 zt_stock 表获取
    2. 表中没有则从下游接口获取
    """
    stock = await get_stock_from_db(code, trade_date)
    if stock:
        print(f"  [DB] 找到股票: {stock.name} ({stock.code})")
        return stock

    print(f"  [API] 从下游接口获取股票: {code}")
    stock = await get_stock_from_api(code, trade_date)
    if stock:
        print(f"  [API] 找到股票: {stock.name} ({stock.code})")
    else:
        print(f"  [API] 未找到股票: {code}")
    return stock


async def test_check_stock_all_rules(stock: ZtStockInfo, prev_workday: str, target_date: str):
    """测试单只股票规则检查"""
    print(f"\n{'='*60}")
    print(f"测试股票: {stock.name} ({stock.code})")
    print(f"涨停日(前一交易日): {prev_workday}")
    print(f"目标日: {target_date}")
    print(f"{'='*60}")

    result = await check_stock_all_rules(stock, prev_workday, target_date)
    print(f"规则检查结果: {'通过 ✓' if result else '未通过 ✗'}")
    return result


async def main():
    parser = argparse.ArgumentParser(description="测试 filter_stock_n 规则")
    parser.add_argument("--date", default="2026-03-25", help="目标日期 (YYYY-MM-DD)")
    parser.add_argument("--stock-code", required=True, help="股票代码")
    parser.add_argument("--prev-date", help="涨停日/前一交易日 (YYYY-MM-DD)，不传则自动计算")
    args = parser.parse_args()

    target_date = args.date
    prev_workday = args.prev_date or get_prev_workday(target_date)

    print(f"目标日: {target_date}")
    print(f"涨停日(前一交易日): {prev_workday}")
    print(f"股票代码: {args.stock_code}")

    # 获取股票数据
    stock = await get_stock(args.stock_code, prev_workday)
    if not stock:
        print(f"\n错误: 无法获取股票 {args.stock_code} 在 {prev_workday} 的涨停数据")
        await close_mysql_engine()
        return

    # 测试规则检查
    await test_check_stock_all_rules(stock, prev_workday, target_date)

    await close_mysql_engine()
    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
