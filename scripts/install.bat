@echo off
REM Installation script for AI Voice Assistant (Windows)
cd /d %~dp0..

echo ==================================
echo AI Voice Assistant Installer
echo ==================================
echo.

REM Check Python version
echo Checking Python version...
python --version 2>nul | findstr /R "3\.[1-9][0-9]" >nul
if errorlevel 1 (
    echo Error: Python 3.10 or higher is required
    exit /b 1
)
echo [OK] Python found
echo.

REM Check if Ollama is installed
echo Checking for Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo Ollama not found. Please install from https://ollama.ai
    echo After installing Ollama, run this script again.
    pause
    exit /b 1
)
echo [OK] Ollama is installed
echo.

REM Pull Ollama model
echo Checking Ollama model...
ollama list | findstr "llama3.2:3b" >nul
if errorlevel 1 (
    echo Pulling llama3.2:3b model (this may take a few minutes)...
    ollama pull llama3.2:3b
) else (
    echo [OK] llama3.2:3b model found
)
echo.

REM Create virtual environment
echo Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencies installed
echo.

REM Install package
echo Installing AI Voice Assistant package...
python setup.py develop
echo [OK] Package installed
echo.

REM Download Piper voice model
echo Checking Piper voice model...
if not exist "models\piper\en_US-lessac-medium.onnx" (
    echo Downloading Piper voice model...
    cd models\piper
    curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -o en_US-lessac-medium.onnx
    curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -o en_US-lessac-medium.onnx.json
    cd ..\..
    echo [OK] Piper voice model downloaded
) else (
    echo [OK] Piper voice model exists
)
echo.

REM Create .env file
if not exist ".env" (
    echo Creating .env configuration file...
    copy .env.example .env
    echo [OK] .env created
) else (
    echo [OK] .env exists
)
echo.

echo ==================================
echo Installation Complete! 🎉
echo ==================================
echo.
echo To get started:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run the CLI: assistant-cli
echo   3. Or try: python examples\simple_query.py
echo.
echo For more information, see README.md or QUICKSTART.md
echo.
pause
