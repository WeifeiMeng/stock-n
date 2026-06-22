# Docker 部署文档

## 环境要求

- Docker Engine >= 20.10
- Docker Compose >= 2.0
- 外部 MySQL 8.0+ 服务（需自行准备）

## 项目结构

```
stock-n/
├── backend/
│   ├── .env.example      # 配置模板
│   └── .env              # MySQL 配置（按需修改）
├── frontend/
├── docker-compose.yml
└── docs/deploy.md
```

## 快速启动

### 1. 配置 MySQL

将 `backend/.env.example` 复制为 `backend/.env`，修改其中的 MySQL 连接信息：

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入实际的 MySQL 地址、密码等
```

默认内容如下：

```bash
MYSQL_HOST=localhost    # Docker 部署时改为 host.docker.internal 或宿主机 IP
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=stocks
```

> **Docker 部署注意**：容器内 `localhost` 指向容器自身，不是宿主机。
> - Windows/Mac Docker Desktop：设为 `host.docker.internal`
> - Linux：设为你宿主机的局域网 IP（如 `192.168.x.x`）

### 2. 启动服务

在项目根目录执行：

```bash
cd /path/to/stock-n
docker compose up -d
```

等待约 30-60 秒，后端启动后前端自动可用。

### 3. 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| N 规则股票池 | `http://服务器IP/stock-n.html` | 主页面 |
| 计算器首页 | `http://服务器IP/` | 原计算器页面 |
| API 文档 | `http://服务器IP:8000/docs` | Swagger 文档 |
| 健康检查 | `http://服务器IP:8000/health` | 后端健康检查 |

> 前端页面（80 端口）通过 Nginx 自动代理 API 请求到后端（8000 端口），浏览器只需访问 80 端口。

## 手动分步部署

### 1. 构建并启动后端

```bash
cd backend

# 构建镜像
docker build -t stock-n-backend .

# 运行容器（需先确保 backend/.env 中 MySQL 配置正确）
docker run -d \
  --name stock-calculator-backend \
  -p 8000:8000 \
  --env-file .env \
  stock-n-backend
```

### 2. 构建并启动前端

```bash
cd frontend

# 构建镜像
docker build -t stock-n-frontend .

# 运行容器
docker run -d \
  --name stock-calculator-frontend \
  -p 80:80 \
  stock-n-frontend
```

## 构建命令速查

```bash
# 只构建后端镜像
docker compose build backend

# 只构建前端镜像
docker compose build frontend

# 构建所有镜像
docker compose build

# 重新构建并启动（代码变更后使用）
docker compose up -d --build
```

## 管理命令

```bash
# 启动所有服务（后台）
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 查看某个服务日志
docker compose logs -f backend

# 重启某个服务
docker compose restart backend

# 停止所有服务
docker compose down
```

## 验证部署

```bash
# 查看所有容器状态
docker compose ps

# 检查后端健康
curl http://localhost:8000/health

# 检查前端
curl -I http://localhost/stock-n.html

# 查看后端日志
docker compose logs backend
```
