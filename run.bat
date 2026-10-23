@echo off
echo Starting MoneyMap...
echo.

:: Start backend
echo [1/2] Starting FastAPI backend on http://localhost:8000
start "MoneyMap Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting Vite frontend on http://localhost:5173
start "MoneyMap Frontend" cmd /k "cd /d %~dp0frontend && C:\Program Files\nodejs\npm.cmd run dev"

echo.
echo MoneyMap is starting up!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API docs: http://localhost:8000/docs
echo.
echo Close the two terminal windows to stop.
