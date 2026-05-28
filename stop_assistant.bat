@echo off
echo ============================================================
echo Stopping AI Voice Assistant
echo ============================================================
echo.

echo Stopping Backend Server...
taskkill //F //FI "WINDOWTITLE eq AI Voice Assistant - Backend*" >nul 2>&1

echo Stopping Wake Word Detection...
taskkill //F //FI "WINDOWTITLE eq AI Voice Assistant - Wake Word*" >nul 2>&1

echo.
echo ============================================================
echo AI Voice Assistant Stopped
echo ============================================================
pause
