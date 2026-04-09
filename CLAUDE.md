# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) about working with this codebase.

## Project Overview

Stock price calculator with FastAPI backend and vanilla HTML/CSS/JS frontend. The backend calculates three buy levels (1.04x, 1.03x, 1.02x current price) and corresponding stop-loss prices (95% of buy price).

## Project Structure

```
stock-n/
├── backend/              # FastAPI backend service
│   ├── src/
│   │   ├── api/         # API routes and models
│   │   ├── dao/         # Data access objects
│   │   ├── service/     # Business logic
│   │   ├── stock_service/# Stock data service
│   │   └── vo/          # Value objects
│   ├── scripts/         # Scripts (filter_stock_n.py, test_filter_rules.py)
│   └── main.py          # Application entry point
├── frontend/            # Frontend (HTML/CSS/JS)
│   ├── index.html      # Original calculator page
│   └── stock-n.html    # N-rule stock pool page
├── start.bat           # One-click startup (Windows)
├── start.sh            # One-click startup (Linux/Mac)
└── docker-compose.yml   # Docker orchestration
```

## Key Commands

### One-Click Startup
```bash
# Windows
./start.bat

# Linux/Mac
chmod +x start.sh && ./start.sh
```

### Backend
```bash
cd backend
uv sync              # Install dependencies
uv run python main.py  # Run development server
```

### Frontend
```bash
cd frontend
python -m http.server 8080
# Access: http://localhost:8080/stock-n.html
```

### Docker
```bash
docker-compose up -d     # Start all services
docker-compose down      # Stop services
docker-compose logs -f   # View logs
```

## Frontend (stock-n.html)

N 规则股票池页面，主要功能：

### 价格计算规则
- 基准价来自后端 `base_price`
- 买1 = 基准价 × 1.03
- 买2 = 基准价 × 1.04
- 买3 = 基准价 × 1.05
- 止盈 = 买入价 × 1.05（红色显示）
- 止损 = 买入价 × 0.95（绿色显示）

### 功能特性
- 深色/浅色主题切换（默认浅色，保存到 localStorage）
- 自动加载当前日期数据
- 日期切换自动刷新
- PDF 导出（使用 html2pdf.js CDN）
- 警示高亮：当止盈 > 当前价时，该行前4列（股票代码、名称、当前价、基准价）标深红色

### API
- `GET /stock-n/{date}` - 获取指定日期的 N 规则股票列表
- 返回字段：`code`, `name`, `current_price`, `base_price`

## Testing

```bash
# Test filter rules
cd backend
uv run python scripts/test_filter_rules.py --date 2026-03-25 --stock-code 000001
```

## Important Notes

- Backend runs on port 8000, frontend on port 80 (via nginx in docker) or 8080 (local)
- The frontend makes direct API calls to `http://localhost:8000` when opened standalone
- MySQL support is optional; backend works without it
- Python 3.12+ recommended; Python 3.13 may have Docker build issues (use `Dockerfile.stable`)
