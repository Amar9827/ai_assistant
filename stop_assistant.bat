@echo off
echo ============================================================
echo Stopping AI Voice Assistant
echo ============================================================
echo.

echo Stopping Wake Word Listener...
taskkill //F //FI "WINDOWTITLE eq AI Voice Assistant*" >nul 2>&1

echo Stopping Backend Server (if running)...
taskkill //F //FI "IMAGENAME eq python.exe" //FI "WINDOWTITLE eq *server*" >nul 2>&1

echo Stopping Frontend (if running)...
taskkill //F //FI "WINDOWTITLE eq *vite*" >nul 2>&1

echo.
echo ============================================================
echo AI Voice Assistant Stopped
echo ============================================================
pause
