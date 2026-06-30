# DDD 分层重构完成报告

日期: 2026-06-22
分支: feat/init-day

## 重构目标

将 `backend/` 从脚本驱动的混乱结构重构为 DDD 四层架构（domain / application / infrastructure / presentation），消除代码重复，修复 8 个已发现的 bug。

## 最终目录结构

```
backend/
├── main.py
├── pyproject.toml
├── src/
│   ├── domain/                          # 领域层 — 纯逻辑，无框架依赖
│   │   ├── model.py                     # DayStockInfo, ZtStockInfo, StockNInfo
│   │   └── rules.py                     # is_zt, is_dt, filter_st_bj, get_market, 日历函数
│   ├── application/                     # 应用层 — 业务编排，通过 Protocol 依赖
│   │   ├── protocols.py                 # DayDataProvider, ZtApiClient, StockRepository
│   │   ├── filter_stock_n.py            # N规则筛选（合并原 filter_stock_n.py + n_calculate.py）
│   │   └── price_calculate.py           # 价格计算
│   ├── infrastructure/                  # 基础设施层 — 实现具体技术
│   │   ├── database/
│   │   │   ├── base.py                  # 统一 Base(DeclarativeBase)
│   │   │   ├── entities.py              # 3个 ORM Entity
│   │   │   ├── connection.py            # MySQL 引擎/session
│   │   │   └── repositories.py          # ZtStock/DayStock/StockN Repository
│   │   └── external/
│   │       └── zhitu_api.py             # httpx 异步 API 客户端
│   └── presentation/                    # 表示层 — FastAPI 路由/模型
│       ├── app.py
│       ├── routes.py
│       ├── deps.py                      # 依赖注入适配器
│       └── models.py                    # Pydantic 模型
├── scripts/
│   └── test_filter_rules.py             # 测试脚本
└── log/
```

## 已删除的文件

| 旧路径 | 原因 |
|--------|------|
| `src/api/` | 迁到 `presentation/` |
| `src/service/` | 迁到 `domain/` + `application/` |
| `src/stock_service/` | 迁到 `infrastructure/external/` |
| `src/vo/` | 迁到 `domain/model.py` |
| `src/middleware/` | 迁到 `infrastructure/database/connection.py` |
| `src/dao/` | 迁到 `infrastructure/database/repositories.py` |
| `scripts/filter_stock_n.py` | 迁到 `application/filter_stock_n.py` |
| `scripts/query_zt_stock.py` | 废弃 |
| `scripts/save_zt_stock.py` | 废弃 |

## API 端点变更

| 旧端点 | 新端点 | 说明 |
|--------|--------|------|
| `POST /calculate` | 删除 | 合并到 /stock-n/filter |
| `POST /stock-n/run-filter/{date}` | 删除 | subprocess 方式,替换为 /stock-n/filter |
| — | `POST /stock-n/filter` | **新增** body: `{"date":"2026-06-22"}` |
| `GET /stock-n/{date}` | 不变 | |
| `GET /` | 不变 | |
| `GET /health` | 不变 | |
| — | `GET /calculate-price` | **新增** 价格计算 |

关键变化: `/stock-n/filter` 是直接的 async 函数调用，不再是 subprocess 执行脚本。

## Bug 修复

| # | Bug | 旧代码位置 | 修复方式 |
|---|-----|-----------|---------|
| 1 | 规则5切片 `[-25:-2]` 只取23天 | `filter_stock_n.py:357` | 改为 `[-31:-1]` / `[:-1]` |
| 2 | 规则4切片 `[-8:-1]` 含涨停日且天数不足 | `filter_stock_n.py:323` | 改为 `[-10:-2]`, min_records=10 |
| 3 | 步骤3按索引取值不验证日期 | `filter_stock_n.py:303` | 按 `date` 字段精确匹配 |
| 4 | `_is_zt` 有 `+0.01` 补偿, `ZT_THRESHOLD=1.096` | `n_calculate.py:99` | 统一为 `>= 1.095`, 去除补偿 |
| 5 | `_is_dt` 隐式 `curr<=0` 逻辑 | `n_calculate.py:103` | 显式化 `curr<=0` 检查 |
| 6 | `requests.get()` 阻塞事件循环 | `ztapi.py` 全部 | 改用 `httpx.AsyncClient` |
| 7 | 三个 DAO 各自定义 `Base(DeclarativeBase)` | 各 dao 文件 | 统一为 `infrastructure/database/base.py` |
| 8 | `_get_n_prev_workday` 无时区 | `filter_stock_n.py:139` | 统一 `tzinfo=UTC+8` |

## 架构决策

- **Protocol 接口解耦**: 应用层通过 `typing.Protocol` 定义依赖接口，基础设施层实现适配器，可替换
- **MySQLSessionMiddleware 移除**: 不再用请求级中间件自动创建 session，改为 FastAPI `Depends` 显式注入
- **Repository 替代 DAO**: session 始终作为显式参数，去掉旧 DAO 的"无 session 自动创建"双模式
- **统一 ORM Base**: 所有 Entity 共享一个 `DeclarativeBase`，支持跨表操作

## git 提交记录

```
0f4e101 fix: minor type hints and docstrings in domain rules
773a748 fix: remove redundant imports, replace deprecated List with list, add docstring
5dc2768 fix: guard sleep on last retry attempt, add request interval to get_zt_stock_list
0934243 fix: filter ST/BJ before saving zt_stocks to DB
6ae7925 feat: add domain layer with pure model and rules, fix is_zt/is_dt bugs
d51d2d2 feat: add infrastructure database layer with unified Base and Repository pattern
0ed679b feat: add async httpx API client
483280a feat: add application layer with merged filter pipeline and bug fixes
f2778fc feat: add presentation layer with FastAPI app, routes, models, and deps
dc0c20a fix: update test script and frontend for new API endpoints
6d50de7 refactor: remove old module structure, finalize DDD migration
```

## 验证结果

- 全量 import 检查: ✅ 通过
- 领域层单元测试: ✅ is_zt / is_dt / get_market / filter_st_bj 全部通过
- 服务器启动: ✅ 无导入错误
- Health check: ✅ `{"status":"healthy"}`
- API root: ✅ `{"message":"股票价格计算API","version":"2.0.0"}`
