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
│   │   ├── service/     # Business logic
│   │   ├── stock_service/# Stock data service
│   │   └── vo/          # Value objects
│   └── main.py          # Application entry point
├── frontend/            # Frontend (HTML/CSS/JS)
└── docker-compose.yml   # Docker orchestration
```

## Key Commands

### Backend
```bash
cd backend
uv sync              # Install dependencies
uv run python main.py  # Run development server
```

### Docker
```bash
docker-compose up -d     # Start all services
docker-compose down      # Stop services
docker-compose logs -f   # View logs
```

### Frontend
```bash
cd frontend
python -m http.server 8080  # Local dev server
```

## Important Notes

- Backend runs on port 8000, frontend on port 80 (via nginx in docker) or 8080 (local)
- The frontend makes direct API calls to `http://localhost:8000` when opened standalone
- MySQL support is optional; backend works without it
- Python 3.12+ recommended; Python 3.13 may have Docker build issues (use `Dockerfile.stable`)
