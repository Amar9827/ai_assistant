@echo off
echo ============================================================
echo Starting AI Voice Assistant with Wake Word Detection
echo ============================================================
echo.

cd /d %~dp0
call venv\Scripts\activate.bat

echo [1/2] Starting Backend Server...
start "AI Voice Assistant - Backend" cmd /k "venv\Scripts\activate && python backend\server.py"
timeout /t 3 /nobreak >nul

echo [2/2] Starting Wake Word Detection...
start "AI Voice Assistant - Wake Word" cmd /k "venv\Scripts\activate && python run_wake_word.py"

echo.
echo ============================================================
echo AI Voice Assistant Started!
echo ============================================================
echo.
echo Two windows have opened:
echo   1. Backend Server (port 8000)
echo   2. Wake Word Detection (listening for "Hey Jarvis")
echo.
echo Both will run continuously until you close them.
echo.
echo Frontend: http://localhost:5173
echo Say "Hey Jarvis" to activate!
echo.
echo ============================================================
pause
