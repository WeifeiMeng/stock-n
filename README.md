# Stock N

Stock N 是一个基于 **FastAPI + Vue 3 + Vite** 的股票 N 规则筛选与价格测算工具。

项目包含后端 API、前端单页应用、Docker 构建与部署脚本。后端负责从数据源读取股票数据、执行 N 规则筛选、写入/查询 MySQL，并提供价格计算接口；前端用于按交易日查询股票池、运行筛选流程、展示买入价/止盈价/止损价，并支持导出 PDF。

## 功能概览

- N 规则股票池筛选：按指定日期执行完整筛选流程。
- 实时筛选进度：通过 SSE 接口推送筛选过程。
- 股票池查询：按交易日查询已入库的 N 规则股票列表。
- 价格测算：根据基准价计算三档买入价、止盈价和止损价。
- PDF 导出：前端可导出当前股票池表格。
- 明暗主题：前端支持浅色/深色主题切换。
- Docker 部署：支持本地构建、生产镜像启动和离线 tar 包上传部署。

## 技术栈

- 后端：Python 3.13+、FastAPI、Uvicorn、SQLAlchemy 2.0、aiomysql、httpx、pandas、uv
- 前端：Vue 3、Vite、html2pdf.js、npm
- 部署：Docker、Docker Compose、Nginx
- 数据库：MySQL

## 项目结构

```text
stock-n/
  backend/
    src/
      application/            应用层，筛选流程和价格计算
      domain/                 领域模型和 N 规则判断
      infrastructure/
        database/             MySQL 连接、ORM Entity、Repository
        external/             外部股票数据 API 客户端
      presentation/           FastAPI 应用、路由和 Pydantic 模型
    main.py                   后端启动入口
    pyproject.toml            Python 依赖和项目版本
    Dockerfile                后端镜像构建
  frontend/
    src/
      App.vue                 前端主页面
      main.js                 Vue 入口
      styles.css              全局样式
    index.html                Vite HTML 入口
    package.json              前端依赖、脚本和版本
    nginx.conf                生产环境 Nginx 静态资源与 API 代理
    Dockerfile                前端镜像构建
  scripts/
    read-version.mjs          读取前后端版本的辅助脚本
  docker-compose.yml          本地 Docker Compose
  docker-compose.prod.yml     生产环境 Docker Compose
  docker-build.sh             构建前后端 Docker 镜像
  docker-push.sh              导出镜像 tar 并上传服务器
  start.bat                   Windows 旧版一键启动脚本
  start.sh                    Linux/macOS 旧版一键启动脚本
  DOCKER.md                   Docker 部署详细说明
```

## 环境变量

后端会按以下优先级读取配置：

```text
系统环境变量 > backend/.env.local > backend/.env
```

MySQL 配置示例：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=stocks
```

首次本地运行时可以复制示例配置：

```bash
cd backend
cp .env.example .env
```

## 本地开发

### 1. 启动后端

```bash
cd backend
uv sync
uv run python main.py
```

后端默认地址：

```text
http://localhost:8000
```

API 文档：

```text
http://localhost:8000/docs
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发地址：

```text
http://localhost:5173
```

Vite 开发服务器会把以下路径代理到 `http://localhost:8000`：

```text
/health
/stock-n
/calculate-price
/api
```

### 3. 构建前端

```bash
cd frontend
npm run build
```

构建产物输出到：

```text
frontend/dist/
```

## Docker 运行

本地构建并启动：

```bash
docker compose up -d --build
```

访问地址：

```text
前端：http://localhost
后端：http://localhost:8000
健康检查：http://localhost:8000/health
API 文档：http://localhost:8000/docs
```

查看日志：

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
```

停止服务：

```bash
docker compose down
```

更多镜像构建、版本号、服务器上传和生产启动说明见 [DOCKER.md](./DOCKER.md)。

## 常用 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | API 基本信息 |
| `GET` | `/health` | 健康检查 |
| `POST` | `/stock-n/filter` | 执行指定日期的 N 规则筛选 |
| `GET` | `/stock-n/filter/stream?date=YYYY-MM-DD` | 通过 SSE 执行筛选并推送实时进度 |
| `GET` | `/stock-n/{date}` | 查询指定日期的 N 规则股票池 |
| `GET` | `/calculate-price?current_price=10.5` | 简单价格计算 |
| `POST` | `/calculate` | 兼容旧前端的价格计算接口 |
| `POST` | `/api/calculate` | 兼容旧前端的价格计算接口 |

### 执行筛选

```bash
curl -X POST "http://localhost:8000/stock-n/filter" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-06-22"}'
```

### 查询股票池

```bash
curl "http://localhost:8000/stock-n/2026-06-22"
```

返回字段：

```json
[
  {
    "code": "000001",
    "name": "示例股票",
    "current_price": 10.5,
    "base_price": 10.0
  }
]
```

### 价格计算

```bash
curl "http://localhost:8000/calculate-price?current_price=10.5"
```

## 前端价格规则

前端股票池页面以 `base_price` 为基准价，计算三档价格：

```text
买 1 = 基准价 * 1.03
买 2 = 基准价 * 1.04
买 3 = 基准价 * 1.05
止盈 = 买入价 * 1.05
止损 = 买入价 * 0.95
```

当任一档止盈价高于当前价时，页面会对该股票行进行提示标记。

## 版本与镜像

默认镜像版本来自项目文件：

```text
后端：backend/pyproject.toml 的 project.version
前端：frontend/package.json 的 version
```

当前默认镜像名：

```text
stock-calculator-backend:0.1.0
stock-calculator-frontend:0.1.0
```

可以通过环境变量覆盖构建版本：

```bash
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-build.sh
```

或使用同一个 tag：

```bash
IMAGE_TAG=0.1.1 ./docker-build.sh
```

## 注意事项

- 本地开发推荐使用 `frontend` 的 Vite 开发服务器，而不是旧的 `python -m http.server` 静态方式。
- `start.bat` 和 `start.sh` 仍保留在仓库中，但脚本内容偏向旧版静态前端流程。
- `backend/.env.local` 适合存放本地覆盖配置，不应提交。
- `node_modules/`、`frontend/dist/`、`backend/.venv/` 等生成目录不应提交。
- 该项目输出仅供数据分析和工具使用，不构成投资建议。
