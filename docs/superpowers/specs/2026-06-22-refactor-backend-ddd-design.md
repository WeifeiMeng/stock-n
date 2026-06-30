# 后端重构为 DDD 分层架构

日期: 2026-06-22
分支: feat/init-day

## 动机

当前问题:
- `filter_stock_n.py` 作为脚本被 API 通过 subprocess 调用，脆弱且慢
- `filter_stock_n.py` 和 `n_calculate.py` 存在代码重复和逻辑差异
- 目录职责混乱: `api/services.py` 是纯计算, `service/n_calculate.py` 是筛选, `stock_service/ztapi.py` 是外部API
- 三个 DAO 各自定义 `Base(DeclarativeBase)`, 注册表不统一
- 多个已发现的 bug（见下方 Bug 修复清单）

## 目标架构

```
backend/src/
├── domain/                    # 领域层 -- 纯逻辑, 无框架/DB/HTTP依赖
│   ├── model.py               # DayStockInfo, ZtStockInfo, StockNInfo
│   └── rules.py               # 纯函数 + 常量
├── application/               # 应用层 -- 编排, 通过接口访问基础设施
│   ├── filter_stock_n.py      # 合并 filter_stock_n.py + n_calculate.py
│   └── price_calculate.py     # 从 api/services.py 迁入
├── infrastructure/            # 基础设施层 -- 实现接口
│   ├── database/
│   │   ├── connection.py      # MySQL 引擎/session
│   │   ├── base.py            # 唯一的 DeclarativeBase
│   │   ├── entities.py        # 所有 ORM Entity
│   │   ├── repositories.py    # StockRepository, DayDataProvider 实现
│   │   └── init.py            # init_all_tables()
│   ├── external/
│   │   └── zhitu_api.py       # 改用 httpx 异步客户端
│   └── calendar.py            # chinese_calendar 封装
├── presentation/              # 表示层 -- FastAPI路由/模型
│   ├── app.py
│   ├── routes.py
│   ├── deps.py
│   └── models.py
├── scripts/
│   └── test_filter_rules.py   # 适配新 import
└── log/
```

## API 端点

| 端点 | 变更 |
|------|------|
| GET / | 不变 |
| GET /health | 不变 |
| GET /stock-n/{date} | 不变 |
| POST /stock-n/filter | **新** body: `{"date":"2026-06-22"}` |
| POST /calculate | **删除** (合并到 /stock-n/filter) |
| POST /stock-n/run-filter/{date} | **删除** (subprocess 方式,替换为 /stock-n/filter) |

## Bug 修复清单

| # | Bug | 修复 | 严重度 |
|---|-----|------|--------|
| 1 | 规则5切片 [-25:-2] 只取23天, [:-2]多切一天 | 改为 [-31:-1] / [:-1] | 高 |
| 2 | 规则4切片 [-8:-1] 少一天且包含涨停日 | 改为 [-10:-2], min_records=10 | 高 |
| 3 | 步骤3 day_list_3 按索引取值不验证日期 | 按 date 字段精确匹配 | 高 |
| 4 | _is_zt 有 +0.01 补偿而 _is_dt 没有 | 统一去除 +0.01, 阈值调整为 1.095(9.5%) | 中 |
| 5 | _is_dt curr<=0 隐式逻辑 | 显式检查, 与 _is_zt 对称 | 中 |
| 6 | ztapi.py 使用同步 requests | 改用 httpx AsyncClient | 中 |
| 7 | 三个 DAO 各自定义 Base | 统一一个 registry | 低 |
| 8 | _get_n_prev_workday 无时区 | 统一 tzinfo=UTC+8 | 低 |

## 删除的文件

- `src/api/` -- 迁到 presentation/ + application/
- `src/service/` -- 迁到 domain/ + application/
- `src/stock_service/` -- 迁到 infrastructure/external/
- `src/vo/` -- 迁到 domain/model.py
- `src/middleware/` -- 迁到 infrastructure/database/connection.py
- `src/dao/` -- 迁到 infrastructure/database/repositories.py
- `scripts/filter_stock_n.py` -- 成为 application/ 代码

## 前端变更

`frontend/stock-n.html`: API 端点路径从 `/stock-n/run-filter/{date}` 改为 `/stock-n/filter` (POST body)。

