#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.local"

echo "===============================
  启动股票计算器前后端服务
==============================="
echo ""

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "错误: 找不到环境配置文件 $ENV_FILE"
        exit 1
    fi
}

load_env_vars() {
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
}

start_backend() {
    echo "[1/2] 启动后端 (http://localhost:8000) ..."
    cd "$SCRIPT_DIR/backend"
    load_env_vars
    nohup uv run python main.py > /tmp/stock-n-backend.log 2>&1 &
    BACKEND_PID=$!
    echo "后端 PID: $BACKEND_PID"
}

start_frontend() {
    echo "[2/2] 启动前端 (http://localhost:8080) ..."
    cd "$SCRIPT_DIR/frontend"
    nohup python3 -m http.server 8080 > /tmp/stock-n-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "前端 PID: $FRONTEND_PID"
}

wait_for_service() {
    local port=$1
    local name=$2
    local max_attempts=10
    local attempt=0

    echo -n "等待 $name 启动 "
    while [ $attempt -lt $max_attempts ]; do
        if lsof -i :$port > /dev/null 2>&1; then
            echo "✓"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo "✗"
    return 1
}

cleanup() {
    echo ""
    echo "正在停止服务..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && echo "已停止后端 (PID: $BACKEND_PID)"
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && echo "已停止前端 (PID: $FRONTEND_PID)"
    echo "所有服务已停止"
    exit 0
}

check_env_file
start_backend
sleep 2
start_frontend
sleep 1

echo ""
echo "===============================
  检查服务状态..."
echo ""

if wait_for_service 8000 "后端"; then
    echo "✓ 后端服务已就绪: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
else
    echo "✗ 后端服务启动失败，请查看日志: /tmp/stock-n-backend.log"
fi

if wait_for_service 8080 "前端"; then
    echo "✓ 前端服务已就绪: http://localhost:8080/stock-n.html"
else
    echo "✗ 前端服务启动失败，请查看日志: /tmp/stock-n-frontend.log"
fi

echo ""
echo "===============================
  日志文件:"
echo "  后端: tail -f /tmp/stock-n-backend.log"
echo "  前端: tail -f /tmp/stock-n-frontend.log"
echo "==============================="
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

trap cleanup SIGINT SIGTERM
wait
