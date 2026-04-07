# 项目概览

股票 N 规则筛选系统，包含数据采集、规则过滤、价格计算、前端展示完整链路。

## 技术栈

- **后端**：FastAPI + SQLAlchemy (Async) + MySQL (aiomysql)
- **前端**：Vanilla HTML/CSS/JS（单页应用）
- **数据源**：芝树 API（`zhituapi.com`）—— 涨停股票列表、日线历史数据
- **节假日判断**：chinese-calendar
- **容器化**：Docker Compose（Nginx 代理前端，FastAPI 后端）

## 项目结构

```
stock-n/
├── backend/
│   ├── main.py                  # 应用入口，uvicorn 启动
│   └── src/
│       ├── api/                 # FastAPI 路由与数据模型
│       │   ├── app.py           # FastAPI 实例、CORS、路由注册
│       │   ├── routes.py        # API 路由实现
│       │   └── models.py        # Pydantic 请求/响应模型
│       ├── dao/                 # 数据访问层（ORM）
│       │   ├── zt_stock_dao.py  # zt_stock 表（涨停股票）
│       │   ├── day_stock_dao.py # day_stock 表（日线数据）
│       │   └── stock_n_dao.py   # stock_n 表（N 规则结果）
│       ├── service/             # 业务逻辑
│       │   ├── n_calculate.py   # N 规则核心算法
│       │   ├── price_calculate.py
│       │   ├── ztapi.py         # 芝树 API 封装（涨停池、日线数据）
│       │   └── tools.py         # 工具函数（市场判断等）
│       ├── vo/                  # Value Object 数据结构
│       │   └── stock.py         # ZtStockInfo, DayStockInfo, StockNInfo
│       └── middleware/
│           └── mysql.py          # MySQL 连接管理、会话中间件
├── frontend/
│   ├── index.html               # 股票价格计算器页面
│   └── stock-n.html             # N 规则股票池页面
├── scripts/
│   └── filter_stock_n.py        # N 规则完整筛选脚本（定时任务用）
└── docker-compose.yml            # 容器编排
```

## 数据库表

### zt_stock（涨停股票池）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| code | VARCHAR(16) | 股票代码 |
| name | VARCHAR(64) | 股票名称 |
| pri | FLOAT | 涨停价格 |
| zf | FLOAT | 涨幅 % |
| cje | FLOAT | 成交额 |
| lt | FLOAT | 流通市值 |
| zsz | FLOAT | 总市值 |
| hs | FLOAT | 换手率 |
| fbt | VARCHAR(16) | 首次封板时间 |
| lbt | VARCHAR(16) | 最后封板时间 |
| zj | FLOAT | 封板资金 |
| zbc | INT | 炸板次数 |
| lbc | INT | 连板次数 |
| tj | VARCHAR(128) | 涨停统计 |
| trade_date | VARCHAR(10) | 交易日期（YYYY-MM-DD） |

**索引**：`idx_zt_stock_code_trade_date(code, trade_date)`

### day_stock（日线数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| code | VARCHAR(16) | 股票代码 |
| name | VARCHAR(64) | 股票名称 |
| market | VARCHAR(16) | 市场（SH/SZ/IB） |
| industry | VARCHAR(64) | 行业 |
| start_pri | FLOAT | 开盘价 |
| end_pri | FLOAT | 收盘价 |
| highest_pri | FLOAT | 最高价 |
| lowest_pri | FLOAT | 最低价 |
| trade_date | VARCHAR(10) | 交易日期 |

**索引**：`idx_day_stock_code_date(code, trade_date)`

### stock_n（N 规则结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| code | VARCHAR(16) | 股票代码 |
| name | VARCHAR(64) | 股票名称 |
| market | VARCHAR(16) | 市场 |
| industry | VARCHAR(64) | 行业 |
| start_pri | FLOAT | 开盘价 |
| end_pri | FLOAT | 收盘价 |
| highest_pri | FLOAT | 最高价 |
| lowest_pri | FLOAT | 最低价 |
| trade_date | VARCHAR(10) | 交易日期 |
| zt | BOOL | 是否涨停 |
| dt | BOOL | 是否跌停 |
| n | INT | 连板次数 |

**索引**：`idx_stock_n_code_date(code, trade_date)`, `idx_stock_n_date(trade_date)`

## N 规则筛选流程

### 脚本执行流程（filter_stock_n.py）

```
输入：目标日期 date（YYYY-MM-DD）

Step 1. _get_prev_workday(date)  → 前一工作日（涨停日）
Step 2. get_zt_stock_list(prev_workday)  → 从芝树 API 拉取涨停池
Step 3. 过滤 ST/*ST/北交所股票
Step 4. 写入 zt_stock 表
Step 5. filter_by_target_day()  → 过滤目标日涨停/跌停的股票
Step 6. rule_no_zt_no_dt()  → 规则4：涨停前 7 个交易日无跌停、无连续涨停
Step 7. rule_zt_30_days()  → 规则5：涨停前 30 个交易日有涨停
Step 8. save_stock_n()  → 写入 stock_n 表
Step 9. save_day_stocks()  → 写入 day_stock 表（target_date 前两个交易日）
```

### 规则详细说明

**规则4（rule_no_zt_no_dt）**：
- 检查涨停日前 7 个交易日（含涨停日当天）
- 移除：有跌停记录 OR 连续两天涨停的股票
- 保留：无跌停且无连续涨停的股票

**规则5（rule_zt_30_days）**：
- 检查涨停日前 30 个交易日（含涨停日当天）
- 移除：30 个交易日内从未涨停过的股票
- 保留：30 个交易日内有至少一次涨停的股票

**涨跌停判断阈值**（定义在 `n_calculate.py`）：
```python
ZT_THRESHOLD = 1.095   # 涨幅 >= 9.5% 视为涨停
DT_THRESHOLD = 0.905   # 跌幅 >= 9.5% 视为跌停
```

### 工作日计算

使用 `chinese_calendar` 库判断中国法定节假日和调休，
而非简单按工作日（周一至周五）计算。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | API 根路径 |
| GET | `/health` | 健康检查 |
| POST | `/calculate` | 按日期执行 N 规则筛选 |
| GET | `/stock-n/{date}` | 获取指定日期的 stock_n 列表及买卖价格 |

### GET /stock-n/{date} 响应结构

```json
[
  {
    "name": "股票名称",
    "price": 10.50,
    "buy_price": 10.82,
    "take_profit_price": 11.36,
    "stop_loss_price": 10.28
  }
]
```

**计算规则**：
- `buy_price` = 前两个交易日收盘价 × 1.03
- `take_profit_price` = buy_price × 1.05
- `stop_loss_price` = buy_price × 0.95

**数据获取优先级**：day_stock 表（优先）→ 芝树 API（兜底）

## 启动方式

### 本地开发

```bash
# 终端1：后端（端口 8000）
cd backend
uv sync
uv run python main.py

# 终端2：前端（端口 8080）
cd frontend
python -m http.server 8080
# 浏览器打开 http://localhost:8080/stock-n.html
```

### Docker Compose

```bash
cd stock-n
docker-compose up -d
# 后端 http://localhost:8000
# 前端 http://localhost
```

### 定时任务

每日收盘后执行筛选脚本：
```bash
cd backend
uv run python scripts/filter_stock_n.py --date 2026-04-07
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| MYSQL_DSN | MySQL DSN（优先使用） | - |
| MYSQL_HOST | MySQL 主机 | localhost |
| MYSQL_PORT | MySQL 端口 | 3306 |
| MYSQL_USER | 用户名 | root |
| MYSQL_PASSWORD | 密码 | 123456 |
| MYSQL_DATABASE | 数据库名 | stocks |

## 前端页面

- `frontend/index.html` — 股票价格计算器：根据当前价格计算三个买入档位及止损价
- `frontend/stock-n.html` — N 规则股票池：展示 stock_n 数据及买卖价格列表

## 数据源

芝树 API（`zhituapi.com`）：
- 涨停股票池：`GET /hs/pool/ztgc/{date}`
- 日线历史：`GET /hs/history/{code}.{market}/d/n`

API Token：`A7EB52CA-9651-4E41-8905-21AC0EA9F954`

**注意**：日线数据请求间隔 0.5 秒避免限流。
