#!/bin/bash

# Docker 镜像上传脚本
# 将镜像文件和部署脚本上传到服务器

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "Docker 镜像上传脚本"
echo "========================================="


if [ $# -eq 0 ]; then
    echo "使用方法: $0 user@server-ip"
    echo "示例: $0 root@192.168.1.100"
    exit 1
fi

REMOTE_HOST="$1"
REMOTE_PATH="/home/stocks"

echo ""
echo "📋 上传目标"
echo "-----------------------------------------"
echo "服务器: ${REMOTE_HOST}"
echo "路径: ${REMOTE_PATH}"
echo ""

echo "🔍 检查文件..."
FILES=(
    "docker-compose.stable.yml"
    "docker-load.sh"
    "deploy.sh"
    "run_n_rule.sh"
    ".env.production"
    "backend.tar"
    "frontend.tar"
)

for file in "${FILES[@]}"; do
    if [ ! -f "${file}" ]; then
        echo "❌ 缺少文件: ${file}"
        echo "   请先运行 docker-build.sh 和 docker-save.sh"
        exit 1
    fi
    echo "✓ ${file}"
done

echo ""
echo "🚀 开始上传..."
echo "-----------------------------------------"

ssh ${REMOTE_HOST} "mkdir -p ${REMOTE_PATH}"

for file in "${FILES[@]}"; do
    echo "📤 上传 ${file}..."
    scp ${file} ${REMOTE_HOST}:${REMOTE_PATH}/
done

echo ""
echo "✅ 上传完成！"
echo ""
echo "========================================="
echo "下一步：在服务器上执行"
echo "========================================="
echo ""
echo "ssh ${REMOTE_HOST}"
echo "cd ${REMOTE_PATH}"
echo "chmod +x docker-load.sh deploy.sh run_n_rule.sh"
echo "./docker-load.sh"
echo "./deploy.sh"
echo ""