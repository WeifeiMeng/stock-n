#!/bin/bash

# Docker 构建脚本
# 用于快速构建前后端 Docker 镜像

set -e

BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"

echo "🚀 开始构建 Docker 镜像..."

# 构建后端镜像
echo "📦 构建后端镜像..."
docker build --platform linux/amd64 -t ${BACKEND_IMAGE}:latest ./backend

# 构建前端镜像
echo "📦 构建前端镜像..."
docker build --platform linux/amd64 -t ${FRONTEND_IMAGE}:latest ./frontend

echo "✅ 所有镜像构建完成！"
echo ""
echo "镜像列表："
echo "  ${BACKEND_IMAGE}:latest"
echo "  ${FRONTEND_IMAGE}:latest"
echo ""
echo "下一步："
echo "  1. 运行 docker-save.sh 保存镜像"
echo "  2. 将镜像文件传输到服务器"
echo "  3. 在服务器上运行 docker-load.sh 加载镜像"