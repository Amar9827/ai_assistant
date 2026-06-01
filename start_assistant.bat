@echo off
echo ============================================================
echo Starting AI Voice Assistant — Wake Word Listener
echo ============================================================
echo.

cd /d %~dp0
call venv\Scripts\activate.bat

echo Wake word listener will run continuously.
echo Backend + Frontend start automatically when you say "Hey Jarvis".
echo Servers auto-shutdown after 2 minutes of inactivity.
echo.
echo Press Ctrl+C to stop.
echo ============================================================
echo.

python run_wake_word.py
echo ============================================================
pause
