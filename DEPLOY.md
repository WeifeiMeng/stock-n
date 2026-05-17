# 服务器部署指南（Docker 镜像方式）

## 前提条件

- 服务器已安装 Docker 和 Docker Compose

## 部署方式

使用 Docker 镜像方式部署，MySQL 包含在 docker-compose 中一体化管理。

**配置文件在本地配置好，直接上传，服务器无需修改。**

---

## 本地操作（在开发机上执行）

### 1. 构建 Docker 镜像

```bash
cd /Users/vic/Desktop/code/stock-n
./docker-build.sh
```

### 2. 保存镜像为 tar 文件

```bash
./docker-save.sh
```

生成两个文件：
- `backend.tar` - 后端镜像
- `frontend.tar` - 前端镜像

### 3. 上传到服务器

```bash
./docker-upload.sh user@服务器IP
```

上传的文件包括：
- `backend.tar` / `frontend.tar` - Docker 镜像
- `docker-compose.stable.yml` - 容器编排配置
- `docker-load.sh` / `deploy.sh` / `run_n_rule.sh` - 部署脚本
- `.env.production` - 生产环境配置（**已在本地配置好**）

---

## 服务器操作（在服务器上执行）

### 1. 登录服务器

```bash
ssh user@服务器IP
cd /home/stocks
```

### 2. 加载 Docker 镜像

```bash
chmod +x docker-load.sh deploy.sh run_n_rule.sh
./docker-load.sh
```

### 3. 一键部署

```bash
./deploy.sh
```

**无需手动配置，`.env.production` 已包含在上传文件中。**

---

## 📌 访问地址

- 前端页面：http://服务器IP:8080/stock-n.html
- API 文档：http://服务器IP:8000/docs

---

## 🔧 常用命令

```bash
# 查看容器状态
docker-compose -f docker-compose.stable.yml ps

# 查看日志
docker-compose -f docker-compose.stable.yml logs -f

# 查看 MySQL 日志
docker-compose -f docker-compose.stable.yml logs mysql

# 重启服务
docker-compose -f docker-compose.stable.yml restart

# 停止服务
docker-compose -f docker-compose.stable.yml down
```

---

## 📦 数据管理

### 进入 MySQL 容器

```bash
docker-compose -f docker-compose.stable.yml exec mysql mysql -u root -p
```

### 备份数据库

```bash
docker-compose -f docker-compose.stable.yml exec mysql mysqldump -u root -p stocks > backup.sql
```

### 恢复数据库

```bash
cat backup.sql | docker-compose -f docker-compose.stable.yml exec -T mysql mysql -u root -p stocks
```

---

## 🔄 更新部署

### 本地操作

```bash
./docker-build.sh
./docker-save.sh
./docker-upload.sh user@服务器IP
```

### 服务器操作

```bash
cd /home/stocks
docker-compose -f docker-compose.stable.yml down
./docker-load.sh
docker-compose -f docker-compose.stable.yml up -d
```

---

## ⚠️ 故障排查

### 容器启动失败
- 查看日志：`docker-compose -f docker-compose.stable.yml logs`

### MySQL 连接失败
- 确认 MySQL 容器是否健康：`docker-compose -f docker-compose.stable.yml ps mysql`
- 等待 MySQL 完全启动（约 30 秒）

### 修改配置文件

如需修改 MySQL 密码或其他配置，修改 `.env.production` 后重新上传：

```bash
# 本地修改后
./docker-upload.sh user@服务器IP

# 服务器上重启
docker-compose -f docker-compose.stable.yml down
docker-compose -f docker-compose.stable.yml up -d
```