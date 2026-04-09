@echo off
chcp 65001 >nul 2>&1
echo ===============================
echo   Stock-N Backend & Frontend
echo ===============================
echo.

:: Start backend
echo [1/2] Starting backend (http://localhost:8000) ...
cd /d "%~dp0backend"
start "Stock-N Backend" cmd /c "uv run python main.py"

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend (http://localhost:8080) ...
cd /d "%~dp0frontend"
start "Stock-N Frontend" cmd /c "python -m http.server 8080"

echo.
echo ===============================
echo   Services started!
echo   - Backend: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - Frontend: http://localhost:8080/stock-n.html
echo ===============================
echo.
pause
