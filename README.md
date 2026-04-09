# 股票价格计算器

一个前后端分离的股票价格计算服务，基于 FastAPI 后端 + 原生前端构建。

## 项目结构

```
stock-n/
├── backend/              # FastAPI 后端服务
│   ├── src/
│   │   ├── api/         # API 路由和模型
│   │   ├── service/     # 业务逻辑
│   │   ├── stock_service/# 股票数据服务
│   │   └── vo/          # 值对象
│   ├── main.py          # 应用入口
│   └── README.md        # 后端详细文档
├── frontend/            # 前端应用
│   ├── index.html       # 主页面
│   └── README.md        # 前端详细文档
├── docker-compose.yml   # Docker Compose 配置
├── DOCKER.md            # Docker 部署指南
└── README.md            # 本文档
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

启动后访问：
- N 规则股票池：http://localhost:8080/stock-n.html
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 手动运行（开发）

**后端：**

```bash
cd backend
uv sync
uv run python main.py
# 服务地址：http://localhost:8000
# API 文档：http://localhost:8000/docs
```

**前端：**

```bash
cd frontend
python -m http.server 8080
# 访问：http://localhost:8080/stock-n.html
```

### Docker Compose（生产）

```bash
# 启动所有服务
docker-compose up -d

# 服务地址：
# - 前端：http://localhost
# - 后端：http://localhost:8000
# - API 文档：http://localhost:8000/docs
```

## 功能特性

- 计算三个买入价位（当前价格的 1.04、1.03、1.02 倍）
- 为每个买入价位计算止损价（买入价的 95%）
- 响应式 Web 界面
- Docker 支持

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 基本信息 |
| `/health` | GET | 健康检查 |
| `/calculate` | POST | 计算买入价和止损价 |

详细 API 文档请参考 [backend/README.md](backend/README.md)。

## 技术栈

- **后端**：FastAPI、Python、Pydantic
- **前端**：HTML5、CSS3、JavaScript (ES6+)
- **部署**：Docker、Docker Compose

## 环境变量

后端支持以下 MySQL 配置（可选）：

```bash
MYSQL_DSN=mysql+aiomysql://user:password@127.0.0.1:3306/your_db
# 或分项配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=user
MYSQL_PASSWORD=password
MYSQL_DATABASE=your_db
```
