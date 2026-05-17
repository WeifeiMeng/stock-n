#!/bin/bash

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "股票分析系统 - 服务器部署脚本（镜像方式）"
echo "========================================="

echo ""
echo "📋 步骤 1: 检查环境"
echo "-----------------------------------------"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi
echo "✓ Docker 已安装"

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装，请先安装 docker-compose"
    exit 1
fi
echo "✓ docker-compose 已安装"

echo ""
echo "📋 步骤 2: 检查 Docker 镜像"
echo "-----------------------------------------"

BACKEND_IMAGE="stock-calculator-backend"
FRONTEND_IMAGE="stock-calculator-frontend"

if ! docker image inspect ${BACKEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 镜像 ${BACKEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-load.sh 加载镜像"
    exit 1
fi
echo "✓ 后端镜像已存在"

if ! docker image inspect ${FRONTEND_IMAGE}:latest > /dev/null 2>&1; then
    echo "❌ 镜像 ${FRONTEND_IMAGE}:latest 不存在"
    echo "   请先运行 docker-load.sh 加载镜像"
    exit 1
fi
echo "✓ 前端镜像已存在"

echo ""
echo "📋 步骤 3: 检查配置文件"
echo "-----------------------------------------"

if [ ! -f ".env.production" ]; then
    echo "❌ 缺少 .env.production 配置文件"
    echo "   请确保已上传配置文件"
    exit 1
fi
echo "✓ .env.production 已存在"

echo ""
echo "📋 步骤 4: 停止旧服务（如果有）"
echo "-----------------------------------------"
docker-compose -f docker-compose.stable.yml down 2>/dev/null || true
echo "✓ 旧服务已停止"

echo ""
echo "📋 步骤 5: 启动服务"
echo "-----------------------------------------"
docker-compose -f docker-compose.stable.yml up -d
echo "✓ 服务已启动"

echo ""
echo "📋 步骤 6: 等待服务就绪"
echo "-----------------------------------------"
echo "等待 MySQL 就绪..."
for i in {1..60}; do
    if docker-compose -f docker-compose.stable.yml exec -T mysql mysqladmin ping -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" > /dev/null 2>&1; then
        echo "✓ MySQL 已就绪"
        break
    fi
    echo "等待 MySQL... ($i/60)"
    sleep 5
done

echo "等待后端服务就绪..."
for i in {1..30}; do
    if curl -s "http://localhost:8000/health" | grep -q "healthy"; then
        echo "✓ 后端服务健康检查通过"
        break
    fi
    echo "等待后端服务... ($i/30)"
    sleep 5
done

echo ""
echo "📋 步骤 7: 配置定时任务"
echo "-----------------------------------------"

CRON_JOB="0 20 * * * cd $(pwd) && ./run_n_rule.sh >> $(pwd)/log/n_rule.log 2>&1"
if ! (crontab -l 2>/dev/null | grep -q "run_n_rule.sh"); then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✓ 已添加定时任务（每天 20:00 执行）"
else
    echo "✓ 定时任务已存在"
fi

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "📌 访问地址："
echo "   - 前端页面: http://$(hostname -I | awk '{print $1}'):8080/stock-n.html"
echo "   - API 文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "📌 容器状态："
docker-compose -f docker-compose.stable.yml ps
echo ""
echo "📌 常用命令："
echo "   - 查看状态: docker-compose -f docker-compose.stable.yml ps"
echo "   - 查看日志: docker-compose -f docker-compose.stable.yml logs -f"
echo "   - 重启服务: docker-compose -f docker-compose.stable.yml restart"
echo "   - 停止服务: docker-compose -f docker-compose.stable.yml down"
echo ""