"""
FastAPI 应用主文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import root, calculate_prices, health_check
from .models import ZtStockInfoResponse

# 创建FastAPI应用
app = FastAPI(
    title="股票价格计算API",
    description="计算股票买一价、买二价、买三价及其对应的止损价",
    version="1.0.0"
)

# 添加CORS中间件，允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.get("/")(root)
app.post("/calculate", response_model=list[ZtStockInfoResponse])(calculate_prices)
app.get("/health")(health_check)
