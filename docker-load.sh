#!/bin/bash

# Docker 镜像加载脚本
# 在服务器上加载 Docker 镜像

set -e

BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"
BACKEND_TAR="backend.tar"
FRONTEND_TAR="frontend.tar"

echo "🚀 开始加载 Docker 镜像..."

# 检查 tar 文件是否存在
echo "🔍 检查镜像文件..."
if [ ! -f "${BACKEND_TAR}" ]; then
    echo "❌ 错误: 文件 ${BACKEND_TAR} 不存在"
    exit 1
fi

if [ ! -f "${FRONTEND_TAR}" ]; then
    echo "❌ 错误: 文件 ${FRONTEND_TAR} 不存在"
    exit 1
fi

# 加载后端镜像
echo "📦 加载后端镜像..."
docker load -i ${BACKEND_TAR}

# 加载前端镜像
echo "📦 加载前端镜像..."
docker load -i ${FRONTEND_TAR}

echo "✅ 镜像加载完成！"
echo ""
echo "加载的镜像："
docker images | grep -E "(${BACKEND_IMAGE}|${FRONTEND_IMAGE})"
echo ""
echo "下一步："
echo "  运行 deploy.sh 启动服务"