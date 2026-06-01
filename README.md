# 🎤 Local AI Voice Assistant v2.0

A fully local AI voice assistant with **real-time streaming**, **wake word detection**, and a modern web UI. Runs entirely on your machine with **no cloud dependencies**. Your conversations stay 100% private!

## ✨ Features

- 🎙️ **Wake Word Detection**: Activate with "Hey Jarvis" - hands-free operation
- 🎤 **Speech-to-Text**: OpenAI Whisper (small model, 85% accuracy)
- 🤖 **Local LLM**: Ollama with streaming responses (Llama 3.2)
- 🔊 **Text-to-Speech**: Piper TTS with 109 voice options
- 🌐 **Modern Web UI**: React-based with cyberpunk design
- ⚡ **Low Latency**: Concurrent TTS streaming (1.5s to first audio)
- 🎨 **Real-time Visualization**: Live waveform during recording
- 💬 **Multi-turn Conversations**: Full context awareness
- 🔒 **100% Private**: All processing happens locally (including wake word)
- 🌍 **Cross-platform**: Windows, Linux, and macOS

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│  React Frontend (Port 5173)                 │
│  - Real-time waveform visualization         │
│  - Microphone input (MediaRecorder API)     │
│  - Streaming text/audio display             │
│  - Wake word activation UI                  │
└──────────────┬──────────────────────────────┘
               │ WebSocket
┌──────────────▼──────────────────────────────┐
│  FastAPI Backend (Port 8000)                │
│  - WebSocket server (/ws endpoint)          │
│  - Concurrent sentence-by-sentence TTS      │
│  - Wake word trigger API                    │
└──────┬───────┬───────┬───────┬──────────────┘
       │       │       │       │
   ┌───▼──┐ ┌──▼───┐ ┌▼─────┐ │
   │Whisper│ │Ollama│ │Piper │ │
   │ (STT) │ │(LLM) │ │(TTS) │ │
   └───────┘ └──────┘ └──────┘ │
                                │
       ┌────────────────────────────────────┐
       │ Always-On Wake Word Launcher       │
       │ (run_wake_word.py)                 │
       │ - openWakeWord library             │
       │ - Pre-trained "hey_jarvis" model   │
       │ - ONNX inference                   │
       │ - Auto-launches servers on detect  │
       │ - Servers auto-stop after 2m idle  │
       └────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (3.14 recommended)
- **Node.js 18+** and npm (for frontend)
- **Ollama** ([Download here](https://ollama.ai))
- **8GB RAM minimum** (16GB recommended)
- ~5GB free disk space for models

### Installation

**1. Install Ollama and download a model:**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2:3b
```

**2. Clone and setup the project:**
```bash
git clone https://github.com/Amar9827/ai_assistant.git
cd ai_assistant

# Create Python virtual environment
python -m venv venv

# Activate environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt
```

**3. Download Piper TTS voice model:**
```bash
# Create models directory
mkdir -p models/piper

# Download voice model (British English, 109 speakers)
cd models/piper
# Download from: https://github.com/rhasspy/piper/releases
# Example for en_GB-vctk-medium:
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx.json
```

**4. Configure environment:**
```bash
# Copy example config
cp .env.example .env

# Edit .env to customize (optional)
# Default settings work well for most users
```

**5. Install frontend dependencies:**
```bash
cd frontend
npm install
```

### Running the Assistant

#### Option 1: Quick Start (Windows)
```bash
# Start the always-on wake word listener
start_assistant.bat

# Say "Hey Jarvis" — backend + frontend launch automatically
# Servers auto-shutdown after 2 minutes of inactivity
# Wake word listener keeps running for the next activation

# To stop everything:
stop_assistant.bat
```

#### Option 2: Manual Start (All Platforms)
```bash
cd ai_assistant
python run_wake_word.py
# Listens for "Hey Jarvis" continuously
# On detection: launches backend (port 8000) + frontend (port 5173)
# Servers auto-stop after 2 minutes idle
```

#### Option 3: Start Servers Manually (without wake word)

**Terminal 1 - Backend:**
```bash
python backend/server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm run dev
```

**Open in browser:** http://localhost:5173

## 🎮 Usage

### Wake Word Activation (Hands-Free) 🆕
1. Say **"Hey Jarvis"** clearly
2. Screen flashes cyan with popup notification
3. Recording starts automatically (no button click needed!)
4. Speak your question
5. Click **"⏹️ Stop"** when done
6. Watch response stream in real-time

**Note:** Wake word listener must be running (`python run_wake_word.py` or `start_assistant.bat`)

### Voice Input (Manual)
1. Click **"🎤 Voice (Test)"** button
2. Allow microphone permission (first time)
3. Speak your question clearly
4. Click **"⏹️ Stop"** when done
5. Watch text stream in real-time
6. Listen to the audio response!

### Text Input
1. Type your question in the text box
2. Press **Enter**
3. Response streams word-by-word
4. Audio plays automatically

### Features
- **Wake Word Detection**: "Hey Jarvis" activation with visual feedback
- **Live Waveform**: See your voice as you speak
- **Multi-turn Chat**: Conversation history maintained
- **Concurrent Audio**: Audio starts playing after first sentence (fast!)
- **Status Indicator**: Shows current state (listening, processing, speaking)
- **Debounced Detection**: 3-second cooldown prevents multiple triggers

## ⚙️ Configuration

Edit `.env` file to customize:

```env
# Whisper (Speech-to-Text)
WHISPER_MODEL=small          # tiny, base, small, medium, large
WHISPER_DEVICE=auto          # auto, cpu, cuda
WHISPER_COMPUTE_TYPE=int8    # int8, float16, float32

# Ollama (Language Model)
OLLAMA_MODEL=llama3.2:3b     # Or mistral:7b, llama3.1:8b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TEMPERATURE=0.7

# Piper TTS (Text-to-Speech)
PIPER_VOICE=en_GB-vctk-medium    # Must match downloaded voice model
PIPER_SPEAKER=17                  # 0-108, each speaker has different voice

# Audio Settings
SAMPLE_RATE=16000
```

### Wake Word Configuration

The wake word detector uses **openWakeWord** with a pre-trained "hey_jarvis" model. Configuration is in [wake_word/detector.py](wake_word/detector.py) and [run_wake_word.py](run_wake_word.py):

- **Threshold**: `0.4` (range 0.0–1.0, lower = more sensitive)
- **Debounce**: `3.0` seconds between detections
- **Idle timeout**: `120` seconds — servers auto-shutdown after inactivity

**How it works:**
- Pre-trained ML model via openWakeWord (no voice sample recording needed)
- ONNX inference via onnxruntime
- Audio captured at 16kHz mono via sounddevice
- 3-second debounce prevents multiple triggers from one utterance

### Voice Selection

The `en_GB-vctk-medium` model has **109 different speakers**. To choose a different voice:

1. Run the voice testing tool:
```bash
python test_voices.py  # Generates samples for 14 female voices
```

2. Listen to the generated `.wav` files
3. Update `.env` with your favorite speaker ID:
```env
PIPER_SPEAKER=17  # Change this number (0-108)
```

**Popular female voices:**
- Speaker 17 (p238): Smooth & conversational ⭐
- Speaker 11 (p276): Clear & neutral
- Speaker 22 (p230): Warm & friendly
- Speaker 25 (p243): Professional

### Model Options

**For Speed (8GB RAM):**
```env
WHISPER_MODEL=tiny
OLLAMA_MODEL=llama3.2:3b
```
→ Fast responses, good for testing

**Balanced (16GB RAM) - Recommended:**
```env
WHISPER_MODEL=small
OLLAMA_MODEL=llama3.2:3b
```
→ 85% accuracy, ~3-5s responses

**For Quality (32GB+ RAM):**
```env
WHISPER_MODEL=medium
OLLAMA_MODEL=mistral:7b
```
→ Best accuracy, 10-15s responses

## 📊 Performance

### Latency Breakdown (16GB RAM, CPU only)

| Step | Time | Optimization |
|------|------|--------------|
| Voice input | 2-3s | VAD auto-stop |
| Whisper transcription | 1-2s | Small model, int8 |
| LLM first sentence | 1-2s | Streaming |
| TTS per sentence | 0.07s | In-process Piper (25× faster) |
| Complete response | 5-8s | Depends on length |

### Key Optimizations

✅ **In-Process Piper TTS**
- OLD: Subprocess call per sentence (1.794s each)
- NEW: In-process PiperVoice (0.070s each)
- **25.6× faster TTS!**

✅ **Concurrent TTS Streaming**
- Generate audio per sentence → Start playing immediately
- Audio starts while LLM is still generating text

✅ **Improved Whisper Accuracy**
- Upgraded to 'small' model (85% accuracy vs 70%)
- Optimized parameters: beam_size=10, best_of=5
- VAD filter enabled for silence removal

✅ **Real-time Streaming**
- Text appears word-by-word (not batched)
- Audio plays while text still generating
- No buffering delays

## 📁 Project Structure

```
ai-assistant/
├── backend/
│   └── server.py                  # FastAPI WebSocket server (2m idle auto-shutdown)
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   ├── App.css               # Cyberpunk styling + wake word animation
│   │   └── components/
│   │       ├── StatusBar.jsx
│   │       ├── AudioVisualizer.jsx
│   │       └── ConversationPanel.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── src/
│   ├── core/
│   │   ├── stt.py                # Whisper integration
│   │   ├── llm.py                # Ollama integration
│   │   ├── tts.py                # Piper TTS
│   │   ├── audio_utils.py        # Audio I/O
│   │   └── assistant.py          # CLI interface (legacy)
│   └── interfaces/
│       └── cli.py                # Terminal interface
├── config/
│   └── settings.py               # Configuration management
├── models/
│   └── piper/                    # TTS voice models
├── wake_word/
│   ├── __init__.py
│   ├── detector.py               # openWakeWord detector class
│   └── test_detector.py          # Live mic test with score visualization
├── run_wake_word.py              # Always-on launcher (wake word → servers)
├── start_assistant.bat           # Windows: Start wake word listener
├── stop_assistant.bat            # Windows: Stop all services
├── .env                          # Your configuration
├── requirements.txt              # Python dependencies
└── README.md
```

## 🔧 Troubleshooting

**Backend won't start:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve
```

**Frontend shows "Disconnected":**
- Verify backend is running on port 8000
- Check browser console (F12) for errors
- Restart backend server

**Wake word not detecting:**
```bash
# Test detector with score visualization
python -m wake_word.test_detector
# Say "Hey Jarvis" and watch the score bar
# If peak score < 0.4, lower threshold in wake_word/detector.py
```

**Wake word too sensitive (false positives):**
- Increase threshold in `wake_word/detector.py` (default: 0.4)
- Increase debounce_seconds for longer cooldown between detections

**Microphone not working:**
- Allow microphone permission in browser
- Check browser console for permission errors
- Try Chrome/Edge (better WebRTC support)
- Ensure no other apps are using the microphone

**Audio quality issues:**
- Try different PIPER_SPEAKER values (0-108)
- Increase OLLAMA_TEMPERATURE for more varied responses
- Use larger Whisper model for better transcription

**Out of memory:**
- Use smaller models: `WHISPER_MODEL=tiny`, `OLLAMA_MODEL=llama3.2:3b`
- Close other applications
- Enable GPU if available: `WHISPER_DEVICE=cuda`

**Voice not changing:**
- Update PIPER_SPEAKER in `.env`
- Restart backend server
- Clear browser cache

## 🛣️ Roadmap

### Completed ✅
- [x] WebSocket streaming architecture
- [x] React-based modern UI
- [x] Real-time waveform visualization
- [x] Concurrent TTS streaming (low latency)
- [x] Multi-turn conversation support
- [x] Voice selection (109 speakers)
- [x] Improved Whisper accuracy (85%)
- [x] Wake word detection ("Hey Jarvis")
- [x] Local wake word processing (no cloud)
- [x] Auto-start recording on wake word
- [x] In-process Piper TTS (25× faster, 0.07s/sentence)
- [x] Cancellable TTS tasks (Turn-based cancellation)
- [x] Security hardening (CORS lockdown, audio size cap, temp file cleanup)
- [x] Always-on wake word launcher with idle auto-shutdown

### Planned 📋
- [ ] JARVIS-style futuristic UI redesign
- [ ] RAG integration (personal knowledge base)
- [ ] Multi-language support
- [ ] Voice activity detection during response
- [ ] Conversation memory across sessions
- [ ] Desktop app (Electron wrapper)
- [ ] Plugin system for custom tools

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Ollama](https://ollama.ai) - Local LLM hosting
- [Piper](https://github.com/rhasspy/piper) - Text-to-speech
- [openWakeWord](https://github.com/dscripka/openWakeWord) - Wake word detection
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference
- [FastAPI](https://fastapi.tiangolo.com/) - WebSocket backend
- [React](https://react.dev/) - Modern UI framework
- [Vite](https://vitejs.dev/) - Fast build tool

## 📚 Documentation

- [BASELINE.txt](BASELINE.txt) - System baseline and performance measurements
- Architecture diagrams in README (see above)

## 💬 Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/Amar9827/ai_assistant/issues)
- Check [Troubleshooting](#-troubleshooting) section above

---

**Made with ❤️ for local AI enthusiasts**

*Privacy-first • Lightning-fast • Always yours*
