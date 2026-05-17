#!/bin/bash

# Docker 镜像保存脚本
# 将构建好的镜像保存为 tar 文件

set -e

BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"
BACKEND_TAR="backend.tar"
FRONTEND_TAR="frontend.tar"

echo "🚀 开始保存 Docker 镜像..."

# 检查镜像是否存在
echo "🔍 检查镜像是否存在..."
if ! docker image inspect ${BACKEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 错误: 镜像 ${BACKEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-build.sh 构建镜像"
    exit 1
fi

if ! docker image inspect ${FRONTEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 错误: 镜像 ${FRONTEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-build.sh 构建镜像"
    exit 1
fi

# 保存后端镜像
echo "📦 保存后端镜像..."
docker save -o ${BACKEND_TAR} ${BACKEND_IMAGE}:latest

# 保存前端镜像
echo "📦 保存前端镜像..."
docker save -o ${FRONTEND_TAR} ${FRONTEND_IMAGE}:latest

echo "✅ 镜像保存完成！"
echo ""
echo "生成的文件："
echo "  ${BACKEND_TAR}"
echo "  ${FRONTEND_TAR}"
echo ""
echo "下一步："
echo "  将这两个 tar 文件传输到服务器，然后运行 docker-load.sh"