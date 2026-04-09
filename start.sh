#!/bin/bash
echo "==============================="
echo "  启动股票计算器前后端服务"
echo "==============================="
echo ""

# 启动后端
echo "[1/2] 启动后端 (http://localhost:8000) ..."
cd "$(dirname "$0")/backend"
nohup uv run python main.py > /tmp/stock-n-backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "[2/2] 启动前端 (http://localhost:8080) ..."
cd "$(dirname "$0")/frontend"
nohup python -m http.server 8080 > /tmp/stock-n-frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "==============================="
echo "  服务已启动！"
echo "  - 后端: http://localhost:8000"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 前端: http://localhost:8080/stock-n.html"
echo ""
echo "  后端日志: /tmp/stock-n-backend.log"
echo "  前端日志: /tmp/stock-n-frontend.log"
echo "==============================="
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获 Ctrl+C 停止所有服务
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已停止所有服务'; exit" SIGINT SIGTERM

# 保持脚本运行
wait
