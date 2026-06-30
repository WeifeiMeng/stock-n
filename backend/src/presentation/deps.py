"""依赖注入 —— 将基础设施实现适配到应用层协议"""
from src.domain.model import ZtStockInfo, DayStockInfo, StockNInfo
from src.application.protocols import DayDataProvider, ZtApiClient, StockRepository
from src.infrastructure.database.repositories import ZtStockRepository, DayStockRepository, StockNRepository


def _zt_entity_to_info(e) -> ZtStockInfo:
    return ZtStockInfo(
        code=e.code, name=e.name, pri=e.pri, zf=e.zf, cje=e.cje,
        lt=e.lt, zsz=e.zsz, hs=e.hs, fbt=e.fbt, lbt=e.lbt,
        zj=e.zj, zbc=e.zbc, lbc=e.lbc, tj=e.tj,
    )


def _day_entity_to_info(e) -> DayStockInfo:
    return DayStockInfo(
        code=e.code, name=e.name or "", market=e.market or "",
        industry=e.industry or "", start_pri=e.start_pri, end_pri=e.end_pri,
        highest_pri=e.highest_pri, lowest_pri=e.lowest_pri, date=e.trade_date,
    )


def get_day_data_provider() -> DayDataProvider:
    """创建带 DB 缓存的日线数据提供器"""
    class _Provider:
        async def get_day_data(self, code: str, name: str, start_date: str, end_date: str, min_records: int = 2):
            from src.infrastructure.database.connection import get_session_factory
            from src.infrastructure.external.zhitu_api import ZhituApiClient

            sf = get_session_factory()
            if sf is not None:
                async with sf() as session:
                    entities = await DayStockRepository.list_by_codes_and_date_range(
                        session, [code], start_date, end_date
                    )
                infos = [_day_entity_to_info(e) for e in entities]
                if len(infos) >= min_records:
                    return infos
            else:
                infos = []

            # DB 数据不足，调 API
            client = ZhituApiClient()
            try:
                api_days = await client.get_day_detail(start_date, end_date, code, name)
            finally:
                await client.close()
            if not api_days:
                return infos

            # 保存到 DB
            sf2 = get_session_factory()
            if sf2 is not None and api_days:
                async with sf2() as session:
                    await DayStockRepository.insert_many(session, api_days)
                    await session.commit()
            return api_days

    return _Provider()


def get_api_client() -> ZtApiClient:
    from src.infrastructure.external.zhitu_api import ZhituApiClient
    return ZhituApiClient()


def get_stock_repository() -> StockRepository:
    """创建股票数据仓库（适配 Repository 到 StockRepository 协议）"""
    class _Repo:
        async def get_zt_stocks(self, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            sf = get_session_factory()
            if sf is None:
                return []
            async with sf() as session:
                entities = await ZtStockRepository.list_by_trade_date(session, trade_date)
            return [_zt_entity_to_info(e) for e in entities]

        async def save_zt_stocks(self, stocks, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            sf = get_session_factory()
            if sf is None:
                return 0
            async with sf() as session:
                count = await ZtStockRepository.insert_many(session, stocks, trade_date)
                await session.commit()
            return count

        async def delete_stock_n_by_date(self, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            sf = get_session_factory()
            if sf is None:
                return 0
            async with sf() as session:
                count = await StockNRepository.delete_by_trade_date(session, trade_date)
                await session.commit()
            return count

        async def save_stock_n_batch(self, stocks):
            from src.infrastructure.database.connection import get_session_factory
            sf = get_session_factory()
            if sf is None:
                return 0
            async with sf() as session:
                count = await StockNRepository.insert_many(session, stocks)
                await session.commit()
            return count

        async def get_stock_n_list(self, trade_date: str):
            from src.infrastructure.database.connection import get_session_factory
            sf = get_session_factory()
            if sf is None:
                return []
            async with sf() as session:
                entities = await StockNRepository.list_by_trade_date(session, trade_date)
            return [
                StockNInfo(
                    code=e.code, name=e.name, market=e.market, industry=e.industry,
                    start_pri=e.start_pri, end_pri=e.end_pri,
                    highest_pri=e.highest_pri, lowest_pri=e.lowest_pri,
                    date=e.trade_date, zt=e.zt, dt=e.dt, n=e.n, base_price=e.base_price,
                )
                for e in entities
            ]
    return _Repo()
