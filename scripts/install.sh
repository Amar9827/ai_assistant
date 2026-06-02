#!/bin/bash
# Installation script for AI Voice Assistant (Linux/Mac)

set -e
cd "$(dirname "$0")/.."

echo "=================================="
echo "AI Voice Assistant Installer"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Check if Ollama is installed
echo "Checking for Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "✓ Ollama is installed"
fi
echo ""

# Pull Ollama model
echo "Checking Ollama model..."
if ! ollama list | grep -q "llama3.2:3b"; then
    echo "Pulling llama3.2:3b model (this may take a few minutes)..."
    ollama pull llama3.2:3b
else
    echo "✓ llama3.2:3b model found"
fi
echo ""

# Create virtual environment
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Install package
echo "Installing AI Voice Assistant package..."
python setup.py develop
echo "✓ Package installed"
echo ""

# Download Piper voice model
echo "Checking Piper voice model..."
if [ ! -f "models/piper/en_US-lessac-medium.onnx" ]; then
    echo "Downloading Piper voice model..."
    cd models/piper
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
    wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
    cd ../..
    echo "✓ Piper voice model downloaded"
else
    echo "✓ Piper voice model exists"
fi
echo ""

# Create .env file
if [ ! -f ".env" ]; then
    echo "Creating .env configuration file..."
    cp .env.example .env
    echo "✓ .env created"
else
    echo "✓ .env exists"
fi
echo ""

echo "=================================="
echo "Installation Complete! 🎉"
echo "=================================="
echo ""
echo "To get started:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the CLI: assistant-cli"
echo "  3. Or try: python examples/simple_query.py"
echo ""
echo "For more information, see README.md or QUICKSTART.md"
