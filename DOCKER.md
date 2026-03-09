# Docker 部署指南

本项目提供了完整的 Docker 支持，可以轻松地将整个应用打包成 Docker 镜像并运行。

## 项目结构

```
my-n/
├── backend/
│   ├── Dockerfile          # 后端 Dockerfile
│   ├── main.py
│   └── pyproject.toml
├── frontend/
│   ├── Dockerfile          # 前端 Dockerfile
│   └── index.html
├── docker-compose.yml      # Docker Compose 配置
└── .dockerignore
```

## 快速开始

### 方式一：使用 Docker Compose（推荐）

这是最简单的方式，可以一键启动整个应用：

```bash
# 构建并启动所有服务
docker-compose up --build

# 或者在后台运行
docker-compose up -d --build
```

应用启动后：
- 前端访问：http://localhost
- 后端API：http://localhost:8000

### 方式二：单独构建和运行

#### 构建后端镜像

```bash
cd backend
docker build -t stock-calculator-backend .
docker run -p 8000:8000 stock-calculator-backend
```

#### 构建前端镜像

```bash
cd frontend
docker build -t stock-calculator-frontend .
docker run -p 80:80 stock-calculator-frontend
```

**注意**：如果单独运行前端，需要修改前端代码中的 API_URL，因为前端无法通过 Nginx 代理访问后端。

## Docker Compose 命令

```bash
# 启动服务
docker-compose up

# 后台启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 停止并删除卷
docker-compose down -v

# 查看日志
docker-compose logs -f

# 查看特定服务的日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重新构建镜像
docker-compose build

# 重新构建并启动
docker-compose up --build

# 查看运行状态
docker-compose ps
```

## 构建 Docker 镜像

### 构建后端镜像

```bash
docker build -t stock-calculator-backend:latest ./backend
```

### 构建前端镜像

```bash
docker build -t stock-calculator-frontend:latest ./frontend
```

### 查看镜像

```bash
docker images | grep stock-calculator
```

## 推送镜像到 Docker Hub

```bash
# 登录 Docker Hub
docker login

# 标记镜像（替换 your-username 为你的 Docker Hub 用户名）
docker tag stock-calculator-backend:latest your-username/stock-calculator-backend:latest
docker tag stock-calculator-frontend:latest your-username/stock-calculator-frontend:latest

# 推送镜像
docker push your-username/stock-calculator-backend:latest
docker push your-username/stock-calculator-frontend:latest
```

## 环境说明

### 后端服务
- **端口**: 8000
- **健康检查**: http://localhost:8000/health
- **API文档**: http://localhost:8000/docs（如果使用 Docker Compose）

### 前端服务
- **端口**: 80
- **访问地址**: http://localhost
- **API代理**: 通过 Nginx 将 `/api/` 路径代理到后端

## 网络配置

Docker Compose 创建了一个名为 `stock-network` 的桥接网络，前后端服务可以通过服务名互相访问：
- 后端服务名：`backend`
- 前端服务名：`frontend`

## 故障排除

### Python 3.13 镜像拉取失败

如果遇到 `ERROR [internal] load metadata for docker.io/library/python:3.13-slim` 错误，可能是因为：

1. **Python 3.13-slim 镜像尚未在 Docker Hub 上发布**
2. **网络问题导致无法拉取镜像**

**解决方案：**

**方案一：使用稳定版本（推荐）**

使用提供的 `Dockerfile.stable`，它基于 Python 3.12：

```bash
# 修改 docker-compose.yml，将 Dockerfile 改为 Dockerfile.stable
# 或者直接构建
cd backend
docker build -f Dockerfile.stable -t stock-calculator-backend:latest .
```

**方案二：使用非 slim 版本**

修改 `backend/Dockerfile`，将 `FROM python:3.13-slim` 改为 `FROM python:3.13`

**方案三：配置 Docker 镜像加速器**

在中国大陆，可以配置 Docker 镜像加速器：

1. 编辑或创建 `/etc/docker/daemon.json`：
```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

2. 重启 Docker 服务：
```bash
sudo systemctl restart docker  # Linux
# 或重启 Docker Desktop (macOS/Windows)
```

### 端口被占用

如果 80 或 8000 端口被占用，可以修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:80"  # 前端改为 8080
  - "8001:8000"  # 后端改为 8001
```

### 前端无法访问后端

确保：
1. 使用 Docker Compose 启动（推荐），这样前端可以通过 Nginx 代理访问后端
2. 或者单独运行时，修改前端代码中的 API_URL 为后端地址

### 查看容器日志

```bash
# 查看所有日志
docker-compose logs

# 查看后端日志
docker-compose logs backend

# 查看前端日志
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend sh

# 进入前端容器
docker-compose exec frontend sh
```

## 生产环境建议

1. **使用具体的镜像标签**：不要使用 `latest`，使用版本号如 `v1.0.0`
2. **配置 HTTPS**：在生产环境中配置 SSL 证书
3. **限制资源**：在 `docker-compose.yml` 中添加资源限制
4. **使用环境变量**：将敏感配置通过环境变量传入
5. **日志管理**：配置日志轮转和集中日志管理
6. **健康检查**：确保健康检查配置正确
7. **安全扫描**：定期扫描镜像漏洞

## 示例：生产环境 docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    image: your-registry/stock-calculator-backend:v1.0.0
    restart: always
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: your-registry/stock-calculator-frontend:v1.0.0
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M
```
