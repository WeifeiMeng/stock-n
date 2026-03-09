#!/bin/bash

# Docker 镜像打包并推送到远端脚本
# 用于将构建好的镜像打包并上传到远程服务器

set -e

REGISTRY="docker.1ms.run"
BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"
REMOTE_HOST="root@123.56.122.63"
REMOTE_PATH="/usr/vic/stock-images"

BACKEND_TAR="backend.tar"
FRONTEND_TAR="frontend.tar"

echo "🚀 开始打包 Docker 镜像..."

# 检查镜像是否存在
echo "🔍 检查镜像是否存在..."
if ! docker image inspect ${REGISTRY}/${BACKEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 错误: 镜像 ${REGISTRY}/${BACKEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-build.sh 构建镜像"
    exit 1
fi

if ! docker image inspect ${REGISTRY}/${FRONTEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 错误: 镜像 ${REGISTRY}/${FRONTEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-build.sh 构建镜像"
    exit 1
fi

# 打包后端镜像
echo "📦 打包后端镜像..."
docker save -o ${BACKEND_TAR} ${REGISTRY}/${BACKEND_IMAGE}:latest

# 打包前端镜像
echo "📦 打包前端镜像..."
docker save -o ${FRONTEND_TAR} ${REGISTRY}/${FRONTEND_IMAGE}:latest

echo "✅ 镜像打包完成！"
echo ""

# 推送到远端
echo "🚀 开始推送到远端服务器..."
echo "   目标: ${REMOTE_HOST}:${REMOTE_PATH}"

# 推送后端镜像
echo "📤 推送后端镜像..."
scp ${BACKEND_TAR} ${REMOTE_HOST}:${REMOTE_PATH}/

# 推送前端镜像
echo "📤 推送前端镜像..."
scp ${FRONTEND_TAR} ${REMOTE_HOST}:${REMOTE_PATH}/

echo "✅ 镜像推送完成！"
echo ""

# 清理本地 tar 文件（可选）
read -p "是否删除本地 tar 文件? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  清理本地文件..."
    rm -f ${BACKEND_TAR} ${FRONTEND_TAR}
    echo "✅ 清理完成！"
fi

echo ""
echo "✨ 所有操作完成！"
echo ""
echo "在远程服务器上可以使用以下命令加载镜像："
echo "  docker load -i ${REMOTE_PATH}/${BACKEND_TAR}"
echo "  docker load -i ${REMOTE_PATH}/${FRONTEND_TAR}"

