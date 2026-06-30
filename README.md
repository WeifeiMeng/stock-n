# N 规则股票筛选

基于 FastAPI + 原生前端，从涨停股票中按 N 规则筛选候选标的。

## 项目结构

```
stock-n/
├── backend/
│   ├── src/
│   │   ├── domain/                 # 领域层 — 纯业务逻辑
│   │   │   ├── model.py            # DayStockInfo, ZtStockInfo, StockNInfo
│   │   │   └── rules.py            # 涨停/跌停判断、过滤、日历函数
│   │   ├── application/            # 应用层 — 业务编排
│   │   │   ├── filter_stock_n.py   # N 规则筛选（完整流程）
│   │   │   ├── price_calculate.py  # 价格计算
│   │   │   └── protocols.py        # 依赖接口协议
│   │   ├── infrastructure/         # 基础设施层 — DB / 外部 API
│   │   │   ├── database/           # MySQL 连接、ORM Entity、Repository
│   │   │   └── external/           # 智图 API 客户端
│   │   └── presentation/           # 表示层 — FastAPI 路由
│   │       ├── app.py              # 应用入口
│   │       ├── routes.py           # 路由注册
│   │       ├── models.py           # Pydantic 模型
│   │       └── deps.py             # 依赖注入
│   ├── main.py                     # 启动入口
│   └── pyproject.toml
├── frontend/
│   ├── stock-n.html                # N 规则股票池页面
│   └── index.html                  # 价格计算器页面
├── docker-compose.yml
├── start.bat                       # Windows 一键启动
└── start.sh                        # Linux/Mac 一键启动
```

## 快速开始

### 一键启动（推荐）

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

### 手动运行（开发）

**后端：**

```bash
cd backend
cp .env.example .env          # 编辑 .env 填入 MySQL 配置
uv sync
uv run python main.py
# → http://localhost:8000
# → API 文档: http://localhost:8000/docs
```

**前端：**

```bash
cd frontend
python -m http.server 8080
# → http://localhost:8080/stock-n.html
```

### Docker Compose

```bash
docker compose up -d
# → 前端: http://localhost
# → 后端: http://localhost:8000
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 基本信息 |
| `/health` | GET | 健康检查 |
| `/stock-n/filter` | POST | 执行 N 规则筛选 `{"date":"2026-06-22"}` |
| `/stock-n/{date}` | GET | 获取指定日期的 stock_n 列表 |
| `/calculate-price` | GET | 价格计算 `?current_price=10.5` |

## 环境变量

MySQL 配置通过 `.env` / `.env.local` 文件或系统环境变量提供：

```bash
# backend/.env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=stocks
```

优先级：系统环境变量 > `.env.local` > `.env`

## 技术栈

- **后端**：FastAPI, Python 3.13+, SQLAlchemy 2.0, httpx, Pandas
- **前端**：HTML5, CSS3, JavaScript (ES6+)
- **部署**：Docker, Docker Compose
