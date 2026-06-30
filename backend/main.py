"""
应用启动入口
"""
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量：先加载 .env（默认值），再加载 .env.local（本地覆盖）
BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(BACKEND_ROOT / ".env", override=False)
load_dotenv(BACKEND_ROOT / ".env.local", override=True)

import uvicorn
from src.presentation.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
