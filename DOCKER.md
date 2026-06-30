# Docker 部署说明

本文档说明如何把本项目的前端和后端构建成 Docker image，上传到服务器，并在服务器上启动。

## 文件说明

```text
stock-n/
  backend/Dockerfile          后端镜像构建文件
  frontend/Dockerfile         前端镜像构建文件
  frontend/package.json       前端 npm 项目配置，包含前端版本号
  frontend/nginx.conf         前端 Nginx 配置，负责静态文件和 API 代理
  docker-compose.yml          本地构建并启动
  docker-compose.prod.yml     服务器使用已加载镜像启动
  docker-build.sh             本地构建前后端镜像
  docker-push.sh              本地导出镜像 tar 并上传服务器
```

## 前置条件

本地机器需要安装并启动 Docker。Windows 上需要先启动 Docker Desktop。

服务器需要安装 Docker 和 Docker Compose 插件：

```bash
docker version
docker compose version
```

## 本地构建镜像

在项目根目录执行：

```bash
./docker-build.sh
```

默认会构建两个镜像，版本号来自项目文件：

```text
后端版本：backend/pyproject.toml 的 project.version
前端版本：frontend/package.json 的 version
```

当前默认镜像为：

```text
stock-calculator-backend:0.1.0
stock-calculator-frontend:0.1.0
```

可以通过环境变量分别覆盖版本：

```bash
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-build.sh
```

也可以用 `IMAGE_TAG` 同时覆盖前后端版本：

```bash
IMAGE_TAG=0.1.1 ./docker-build.sh
```

如果需要加 registry 前缀：

```bash
REGISTRY=docker.example.com ./docker-build.sh
```

等价的手动构建命令：

```bash
docker build --platform linux/amd64 -t stock-calculator-backend:0.1.0 ./backend
docker build --platform linux/amd64 -t stock-calculator-frontend:0.1.0 ./frontend
```

## 本地启动验证

本地直接构建并启动：

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

停止本地服务：

```bash
docker compose down
```

## 打包并上传到服务器

先构建镜像：

```bash
./docker-build.sh
```

然后导出镜像 tar 包并上传服务器：

```bash
./docker-push.sh
```

脚本默认上传到：

```text
root@123.56.122.63:/usr/vic/stock-images
```

可以通过环境变量覆盖服务器和目录：

```bash
REMOTE_HOST=root@your-server REMOTE_PATH=/opt/stock-n ./docker-push.sh
```

如果构建时覆盖了版本，上传时也要保持一致：

```bash
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-build.sh
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-push.sh
```

上传脚本会把以下文件传到服务器：

```text
backend-<tag>.tar
frontend-<tag>.tar
docker-compose.prod.yml
```

## 服务器加载镜像

登录服务器：

```bash
ssh root@123.56.122.63
cd /usr/vic/stock-images
```

加载镜像：

```bash
docker load -i backend-0.1.0.tar
docker load -i frontend-0.1.0.tar
```

确认镜像存在：

```bash
docker images | grep stock-calculator
```

## 服务器环境变量

在服务器的部署目录创建 `.env`：

```bash
cd /usr/vic/stock-images
vi .env
```

示例：

```env
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=stocks
```

如果 MySQL 也运行在 Docker Compose 网络里，把 `MYSQL_HOST` 改成对应的服务名。

如果 MySQL 运行在服务器宿主机上，推荐使用：

```env
MYSQL_HOST=host.docker.internal
```

`docker-compose.prod.yml` 已经配置了 `host.docker.internal:host-gateway`。

## 服务器启动

在服务器部署目录执行：

```bash
docker compose -f docker-compose.prod.yml up -d
```

查看状态：

```bash
docker compose -f docker-compose.prod.yml ps
```

查看日志：

```bash
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

停止服务：

```bash
docker compose -f docker-compose.prod.yml down
```

## 使用自定义镜像名或 tag 启动

`docker-compose.prod.yml` 默认使用：

```text
stock-calculator-backend:0.1.0
stock-calculator-frontend:0.1.0
```

如果加载的是其他 tag，可以启动时指定：

```bash
BACKEND_IMAGE_REF=stock-calculator-backend:0.1.1 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.1 \
docker compose -f docker-compose.prod.yml up -d
```

如果前端 80 端口被占用，可以改端口：

```bash
FRONTEND_PORT=8080 docker compose -f docker-compose.prod.yml up -d
```

后端端口同理：

```bash
BACKEND_PORT=8001 docker compose -f docker-compose.prod.yml up -d
```

## 更新部署流程

本地重新构建并上传：

```bash
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-build.sh
BACKEND_VERSION=0.1.1 FRONTEND_VERSION=0.1.1 ./docker-push.sh
```

服务器加载新镜像并启动：

```bash
cd /usr/vic/stock-images
docker load -i backend-0.1.1.tar
docker load -i frontend-0.1.1.tar

BACKEND_IMAGE_REF=stock-calculator-backend:0.1.1 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.1 \
docker compose -f docker-compose.prod.yml up -d
```

## 常见问题

### Docker daemon 未启动

如果本地构建时报错类似：

```text
failed to connect to the docker API
```

先启动 Docker Desktop 或 Docker daemon，再重新执行构建命令。

### 后端健康检查失败

查看后端日志：

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

重点检查 `.env` 里的数据库连接信息是否正确。

### 前端无法访问后端

前端容器通过 Nginx 把请求代理到后端服务名 `backend:8000`。请确认两个容器都在运行：

```bash
docker compose -f docker-compose.prod.yml ps
```

### 服务器 MySQL 连接失败

如果 MySQL 在宿主机上，不要把 `MYSQL_HOST` 写成 `localhost`。容器里的 `localhost` 指向容器自己，应使用：

```env
MYSQL_HOST=host.docker.internal
```
