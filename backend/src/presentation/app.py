from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import (
    calculate_price,
    calculate_price_compat,
    get_stock_positions,
    get_stock_n_list,
    health_check,
    root,
    run_filter,
    run_filter_stream,
    update_stock_positions,
)
from .models import FilterRequest, FilterResponse, PositionItem, PositionUpdateResponse, StockNItem
from src.infrastructure.database.repositories import init_all_tables
from src.infrastructure.database.connection import close_mysql_engine

app = FastAPI(
    title="股票价格计算API",
    description="N规则筛选 + 价格计算",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_all_tables()


@app.on_event("shutdown")
async def shutdown():
    await close_mysql_engine()

app.get("/")(root)
app.get("/health")(health_check)
app.post("/stock-n/filter", response_model=FilterResponse)(run_filter)
app.get("/stock-n/filter/stream")(run_filter_stream)
app.post("/stock-position/update", response_model=PositionUpdateResponse)(update_stock_positions)
app.get("/stock-position/{date}", response_model=list[PositionItem])(get_stock_positions)
app.get("/stock-n/{date}", response_model=list[StockNItem])(get_stock_n_list)
app.get("/calculate-price")(calculate_price)
app.post("/api/calculate")(calculate_price_compat)
app.post("/calculate")(calculate_price_compat)
