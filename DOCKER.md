# Docker 部署指南

本文档说明如何把项目构建成 Docker 镜像，并部署到服务器。

## 1. 环境变量怎么处理

后端需要数据库和接口 token 等配置，不要在打镜像时写进镜像。原因是镜像层会保留敏感信息，也不方便不同环境复用。

推荐做法：服务器部署目录放一个 `.env` 文件，启动容器时由 `docker-compose.prod.yml` 读取。

后端会读取这些环境变量：

```env
# 优先级最高；如果配置了 MYSQL_DSN，会忽略下面拆分字段
MYSQL_DSN=mysql+aiomysql://user:password@host:3306/stocks

# 不使用 MYSQL_DSN 时使用下面这些
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=stocks

# 知途 API token，多个用英文逗号分隔
ZT_API_TOKENS=token1,token2
```

如果 MySQL 在服务器宿主机上，`MYSQL_HOST` 用：

```env
MYSQL_HOST=host.docker.internal
```

如果 MySQL 也是 Docker Compose 里的服务，`MYSQL_HOST` 用对应服务名。

## 2. 本地构建镜像

在项目根目录执行：

```bash
./docker-build.sh
```

默认构建：

```text
stock-calculator-backend:<backend version>
stock-calculator-frontend:<frontend version>
```

版本号默认来自：

```text
backend/pyproject.toml
frontend/package.json
```

指定统一版本：

```bash
IMAGE_TAG=0.1.1 ./docker-build.sh
```

指定镜像仓库前缀：

```bash
REGISTRY=registry.example.com/stock-n IMAGE_TAG=0.1.1 ./docker-build.sh
```

## 3. 本地验证

```bash
docker compose up -d --build
```

访问：

```text
前端：http://localhost
后端：http://localhost:8000
健康检查：http://localhost:8000/health
接口文档：http://localhost:8000/docs
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

## 4. 导出并上传镜像到服务器

先构建：

```bash
IMAGE_TAG=0.1.1 ./docker-build.sh
```

再导出 tar 并上传：

```bash
REMOTE_HOST=root@your-server \
REMOTE_PATH=/opt/stock-n \
IMAGE_TAG=0.1.1 \
./docker-push.sh
```

脚本会上传：

```text
backend-0.1.1.tar
frontend-0.1.1.tar
docker-compose.prod.yml
```

默认上传目录是 `/usr/vic/stock-images`，建议按实际服务器改成 `/opt/stock-n` 或你的部署目录。

## 5. 服务器启动

登录服务器：

```bash
ssh root@your-server
cd /opt/stock-n
```

加载镜像：

```bash
docker load -i backend-0.1.1.tar
docker load -i frontend-0.1.1.tar
```

创建服务器 `.env`：

```bash
vim .env
```

示例：

```env
MYSQL_HOST=host.docker.internal
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=stocks
ZT_API_TOKENS=token1,token2
```

启动：

```bash
BACKEND_IMAGE_REF=stock-calculator-backend:0.1.1 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.1 \
docker compose -f docker-compose.prod.yml up -d
```

检查状态：

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

默认端口：

```text
前端：80
后端：8000
```

如果服务器 80 端口被占用：

```bash
FRONTEND_PORT=8080 \
BACKEND_IMAGE_REF=stock-calculator-backend:0.1.1 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.1 \
docker compose -f docker-compose.prod.yml up -d
```

## 6. 更新部署

本地重新构建并上传：

```bash
IMAGE_TAG=0.1.2 ./docker-build.sh

REMOTE_HOST=root@your-server \
REMOTE_PATH=/opt/stock-n \
IMAGE_TAG=0.1.2 \
./docker-push.sh
```

服务器加载并重启：

```bash
cd /opt/stock-n
docker load -i backend-0.1.2.tar
docker load -i frontend-0.1.2.tar

BACKEND_IMAGE_REF=stock-calculator-backend:0.1.2 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.2 \
docker compose -f docker-compose.prod.yml up -d
```

## 7. 常用命令

查看服务：

```bash
docker compose -f docker-compose.prod.yml ps
```

看后端日志：

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

看前端日志：

```bash
docker compose -f docker-compose.prod.yml logs -f frontend
```

停止服务：

```bash
docker compose -f docker-compose.prod.yml down
```

重启服务：

```bash
docker compose -f docker-compose.prod.yml restart
```

## 8. 常见问题

### 后端连不上 MySQL

先看日志：

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

如果 MySQL 在宿主机，不要写 `MYSQL_HOST=localhost`。容器里的 `localhost` 是容器自身，应使用：

```env
MYSQL_HOST=host.docker.internal
```

### 前端打不开接口

前端 Nginx 会把 API 请求代理到 Compose 网络里的 `backend:8000`。确认两个容器都健康：

```bash
docker compose -f docker-compose.prod.yml ps
```

### 想用其他 env 文件

`docker-compose.prod.yml` 支持 `ENV_FILE`：

```bash
ENV_FILE=/opt/stock-n/prod.env \
BACKEND_IMAGE_REF=stock-calculator-backend:0.1.1 \
FRONTEND_IMAGE_REF=stock-calculator-frontend:0.1.1 \
docker compose -f docker-compose.prod.yml up -d
```
