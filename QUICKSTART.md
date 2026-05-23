# Quick Start Guide

Get your AI Voice Assistant running in 5 minutes!

## Step 1: Install Ollama

**Windows:** Download from https://ollama.ai and install

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Pull a model:
```bash
ollama pull llama3.2:3b
```

Verify it's running:
```bash
ollama list
```

## Step 2: Download Piper Voice Model

```bash
cd models/piper

# Windows (using curl):
curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -o en_US-lessac-medium.onnx
curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -o en_US-lessac-medium.onnx.json

# Linux/Mac:
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

cd ../..
```

## Step 3: Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package
python setup.py develop
```

## Step 4: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit if needed (optional)
# The defaults should work for most users
```

## Step 5: Run!

### Option A: CLI Interface (Simplest)

```bash
assistant-cli
```

Choose `text` mode and type your message.

### Option B: Web Interface

```bash
assistant-web
```

Open http://localhost:8000 in your browser.

### Option C: GUI Interface

```bash
assistant-gui
```

Opens automatically at http://localhost:7860

## Testing

Try the example scripts:

```bash
# Simple text query
python examples/simple_query.py

# Multi-turn conversation
python examples/conversation_demo.py

# Full voice interaction (requires microphone)
python examples/voice_demo.py
```

## Troubleshooting

**"Ollama not reachable"**
- Make sure Ollama is running: `ollama serve`
- Check the model is downloaded: `ollama list`

**"Piper model not found"**
- Verify files exist in `models/piper/`
- Check the filenames match `.env` settings

**"No audio device found"**
- Check microphone is connected
- Test with: `python -c "import sounddevice; print(sounddevice.query_devices())"`

**Slow performance?**
- Use smaller models: `WHISPER_MODEL=tiny` in `.env`
- Use GPU if available: `WHISPER_DEVICE=cuda`

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Customize settings in `.env`
- Try different LLM models: `ollama pull mistral:7b`
- Experiment with different Piper voices from https://github.com/rhasspy/piper

Enjoy your local AI assistant! 🎤🤖
