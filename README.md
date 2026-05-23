# 🎤 Local AI Voice Assistant

A fully local AI voice assistant that runs entirely on your machine with **no cloud dependencies**. Your conversations stay private!

## ✨ Features

- 🎤 **Speech-to-Text**: OpenAI Whisper (local inference)
- 🤖 **Local LLM**: Ollama (Llama, Mistral, etc.)
- 🔊 **Text-to-Speech**: Piper TTS
- 🎙️ **Voice Activity Detection**: Auto-stop recording on silence (WebRTC VAD)
- ⚡ **Streaming Pipeline**: Start speaking response while LLM generates (low latency)
- 💻 **Multiple Interfaces**: CLI, Web UI, and Desktop GUI
- 🔒 **100% Private**: All processing happens locally
- 🌍 **Cross-platform**: Windows, Linux, and macOS

## 🏗️ Architecture

```
User Interface (CLI / Web / GUI)
           ↓
    Voice Assistant
    ↓      ↓      ↓
Whisper  Ollama  Piper
  (STT)   (LLM)   (TTS)
```

## 📋 Prerequisites

- Python 3.10 or higher
- 8GB RAM minimum (16GB recommended)
- ~5GB free disk space for models
- Optional: NVIDIA GPU for faster inference

## 🚀 Quick Start

### Automated Installation (Recommended)

**Windows:**
```cmd
install.bat
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

The installer will:
1. Check/install Ollama
2. Download the LLM model
3. Download Piper voice model
4. Set up Python environment
5. Install all dependencies

### Manual Installation

See [QUICKSTART.md](QUICKSTART.md) for detailed manual setup instructions.

## 🎮 Usage

### CLI Interface

```bash
# Activate environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run CLI
assistant-cli
```

Choose from:
- **voice** - Speak to the assistant
- **text** - Type your questions
- **reset** - Clear conversation history
- **quit** - Exit

### Web Interface

```bash
assistant-web
```

Open http://localhost:8000 in your browser.

### Desktop GUI

```bash
assistant-gui
```

Opens automatically at http://localhost:7860

## ⚙️ Configuration

Copy `.env.example` to `.env` and customize:

```env
# Speech-to-Text Model
WHISPER_MODEL=small        # Options: tiny, base, small, medium, large

# Language Model
OLLAMA_MODEL=mistral:7b    # Or llama3.2:3b, llama3.1:8b, etc.

# Text-to-Speech Voice
PIPER_VOICE=en_US-lessac-medium
```

### Recommended Configurations

**For Speed (8GB RAM):**
```env
WHISPER_MODEL=tiny
OLLAMA_MODEL=llama3.2:3b
```
→ 5-10 second voice-to-voice response

**Balanced (16GB RAM):**
```env
WHISPER_MODEL=small
OLLAMA_MODEL=mistral:7b
```
→ 10-18 second response, excellent quality

**For Quality (32GB+ RAM):**
```env
WHISPER_MODEL=medium
OLLAMA_MODEL=llama3.1:70b
```
→ 20-40 second response, GPT-4 level quality

## 📁 Project Structure

```
ai-assistant/
├── config/              # Configuration management
├── src/
│   ├── core/           # Core assistant logic
│   │   ├── assistant.py    # Main orchestration
│   │   ├── stt.py         # Speech-to-text (Whisper)
│   │   ├── llm.py         # LLM interface (Ollama)
│   │   ├── tts.py         # Text-to-speech (Piper)
│   │   └── audio_utils.py # Audio I/O
│   └── interfaces/     # User interfaces
│       ├── cli.py         # Terminal interface
│       ├── web.py         # Web UI (FastAPI)
│       └── gui.py         # Desktop GUI (Gradio)
├── models/             # Downloaded models
├── examples/           # Example scripts
└── tests/              # Unit tests
```

## 🔧 Troubleshooting

**Ollama not connecting:**
```bash
ollama serve  # Start Ollama service
ollama list   # Verify models installed
```

**Audio device errors:**
```python
import sounddevice as sd
print(sd.query_devices())  # List available devices
```

**Out of memory:**
- Use smaller models (Whisper: tiny, Ollama: 3b)
- Close other applications
- Enable quantization: `WHISPER_COMPUTE_TYPE=int8`

**Piper model not found:**
- Verify files in `models/piper/`
- Check filename matches `.env` setting

## 📊 Performance Benchmarks

### Traditional Pipeline (Non-Streaming)
| System | Whisper | LLM | Total Time |
|--------|---------|-----|------------|
| 8GB RAM + CPU | tiny | 3b | 5-10s |
| 16GB RAM + CPU | small | 7b | 10-18s |
| 32GB RAM + GPU | medium | 70b | 15-30s |

### Streaming Pipeline (VAD + Streaming LLM/TTS)
| System | Whisper | LLM | Time to First Word | Total |
|--------|---------|-----|-------------------|--------|
| 16GB RAM + CPU | small | 3b | **5-8s** ⚡ | 8-12s |
| 32GB RAM + CPU | small | 7b | **6-10s** ⚡ | 12-18s |

**Why streaming is faster:**
- VAD eliminates fixed recording delay (saves 2-3s)
- First sentence spoken while remaining response generates
- Perceived latency reduced by 40-60%

## 🛣️ Roadmap

- [x] Voice activity detection (VAD) ✅
- [x] Streaming LLM responses ✅
- [ ] Wake word detection ("Hey Assistant")
- [ ] Multi-language support
- [ ] Plugin system for custom tools
- [ ] Conversation memory across sessions
- [ ] Mobile app interface
- [ ] Interrupt capability (stop mid-response)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Ollama](https://ollama.ai) - Local LLM hosting
- [Piper](https://github.com/rhasspy/piper) - Text-to-speech
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference

## 💬 Support

For issues and questions, please open an issue on GitHub.

---

**Made with ❤️ for local AI enthusiasts**
