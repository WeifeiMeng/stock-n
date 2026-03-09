#!/bin/bash

# Docker 构建脚本
# 用于快速构建前后端 Docker 镜像

set -e

REGISTRY="docker.xuanyuan.run"
BASE_REGISTRY="docker.io"  # 基础镜像从 docker.io 拉取（免费）
BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"

echo "🚀 开始构建 Docker 镜像..."

# 构建后端镜像
echo "📦 构建后端镜像..."
docker build --platform linux/amd64 --build-arg BASE_REGISTRY=$BASE_REGISTRY -t ${REGISTRY}/${BACKEND_IMAGE}:latest ./backend

# 构建前端镜像
echo "📦 构建前端镜像..."
docker build --platform linux/amd64 --build-arg BASE_REGISTRY=$BASE_REGISTRY -t ${REGISTRY}/${FRONTEND_IMAGE}:latest ./frontend

echo "✅ 所有镜像构建完成！"
echo ""
echo "可以使用以下命令运行："
echo "  docker-compose up"
echo ""
echo "或者单独运行："
echo "  docker run -p 8000:8000 stock-calculator-backend:latest"
echo "  docker run -p 80:80 stock-calculator-frontend:latest"
