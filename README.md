# 🎤 AI Voice Assistant — J.A.R.V.I.S. v2.0

A J.A.R.V.I.S.-inspired AI voice assistant with **real-time streaming**, **wake word detection**, **web search**, and a modern web UI. Supports both **cloud (Groq)** and **local (Ollama)** LLMs with automatic fallback.

## ✨ Features

- 🎙️ **Wake Word Detection**: Activate with "Hey Jarvis" — hands-free operation
- 🎤 **Speech-to-Text**: Groq cloud (whisper-large-v3-turbo) with local Whisper fallback
- 🤖 **Dual LLM Support**: Groq cloud (llama-3.3-70b) primary, Ollama local fallback
- 🔊 **Text-to-Speech**: Piper TTS with British male voice (JARVIS persona)
- 🌐 **Web Search**: Tavily-powered real-time search with LLM-based query routing
- 🧠 **JARVIS Persona**: Iron Man-inspired AI personality — formal, composed, witty
- ⚡ **Low Latency**: ~1.5s to first audio, concurrent TTS streaming
- 🌐 **Modern Web UI**: React-based with cyberpunk design
- 🎨 **Real-time Visualization**: Live waveform during recording
- 💬 **Multi-turn Conversations**: Full context awareness with history
- 🛡️ **Resilient**: Automatic Groq→Ollama fallback, rate limit tracking, non-blocking streaming
- 🔒 **Security**: CORS lockdown, audio size caps, temp file cleanup
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
│  - LLM query router (search vs direct)      │
│  - Concurrent sentence-by-sentence TTS      │
│  - Non-blocking LLM streaming (threads)     │
│  - Wake word trigger API                    │
│  - Turn-based cancellation                  │
└──────┬───────┬───────┬───────┬──────────────┘
       │       │       │       │
   ┌───▼──┐ ┌──▼───┐ ┌▼─────┐ ┌▼──────────┐
   │Groq  │ │Groq  │ │Piper │ │Tavily     │
   │Whis- │ │LLM   │ │(TTS) │ │Web Search │
   │per   │ │  ↓   │ └──────┘ └───────────┘
   │(STT) │ │Ollama│
   │  ↓   │ │(fall │
   │Local │ │back) │
   │Whis- │ └──────┘
   │per   │
   └──────┘
                                │
       ┌────────────────────────────────────┐
       │ Always-On Wake Word Launcher       │
       │ (run_wake_word.py)                 │
       │ - openWakeWord library             │
       │ - Pre-trained "hey_jarvis" model   │
       │ - ONNX inference                   │
       │ - Auto-launches servers on detect  │
       │ - Port-reuse detection             │
       └────────────────────────────────────┘
```

### Query Processing Flow

```
User speaks → STT (Groq/Whisper) → Query Router (fast LLM)
                                         │
                               ┌─────────┴──────────┐
                               │                      │
                          Needs search?           No search
                               │                      │
                         Tavily API              Direct to LLM
                               │                      │
                         Rewrite query                 │
                               │                      │
                               └──────────┬───────────┘
                                          │
                                    LLM (Groq → Ollama fallback)
                                          │
                                    Stream response
                                          │
                                    Piper TTS → Audio
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (3.14 recommended)
- **Node.js 18+** and npm (for frontend)
- **Ollama** ([Download here](https://ollama.ai)) — local LLM fallback
- **8GB RAM minimum** (16GB recommended)
- ~5GB free disk space for models

### API Keys (Optional but Recommended)

| Service | Purpose | Free Tier | Get Key |
|---------|---------|-----------|---------|
| **Groq** | Cloud LLM (fast, 70B model) + Cloud STT | 100K tokens/day | [console.groq.com](https://console.groq.com) |
| **Tavily** | Web search for real-time info | 1000 searches/month | [tavily.com](https://tavily.com) |

Without API keys, the assistant runs fully local using Ollama + local Whisper.

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

# Download voice model (British English, JARVIS-like voice)
cd models/piper
# Download from: https://github.com/rhasspy/piper/releases
# Default voice: en_GB-alan-medium (refined British male, similar to JARVIS)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
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
scripts\start_assistant.bat

# Say "Hey Jarvis" — backend + frontend launch automatically
# Servers auto-shutdown after 2 minutes of inactivity
# Wake word listener keeps running for the next activation

# To stop everything:
scripts\stop_assistant.bat
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

**Note:** Wake word listener must be running (`python run_wake_word.py` or `scripts\start_assistant.bat`)

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
# LLM Provider: "groq" (cloud, recommended) or "ollama" (local only)
LLM_PROVIDER=groq

# Groq Configuration (cloud LLM — fast inference)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# STT Provider: "groq" (cloud, best accuracy) or "local" (faster-whisper)
STT_PROVIDER=groq

# Whisper (local STT fallback)
WHISPER_MODEL=small          # tiny, base, small, medium, large
WHISPER_DEVICE=auto          # auto, cpu, cuda
WHISPER_COMPUTE_TYPE=int8    # int8, float16, float32

# Ollama (local LLM fallback)
OLLAMA_MODEL=llama3.2:3b     # Or mistral:7b, llama3.1:8b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TEMPERATURE=0.7

# Tavily Web Search (for real-time information)
TAVILY_API_KEY=your_tavily_api_key_here

# Piper TTS (Text-to-Speech)
PIPER_VOICE=en_GB-alan-medium     # JARVIS-like British male voice
PIPER_SPEAKER=0                    # alan is single-speaker
PIPER_LENGTH_SCALE=0.85            # Slightly faster speech

# Audio Settings
SAMPLE_RATE=16000
```

### Cloud vs Local Modes

**Cloud Mode (Recommended)** — Set `LLM_PROVIDER=groq` and `STT_PROVIDER=groq`:
- Uses Groq's llama-3.3-70b for fast, high-quality responses
- Groq Whisper for accurate transcription
- Automatic fallback to local Ollama/Whisper on rate limit or failure
- Web search enabled via Tavily API

**Local Mode** — Set `LLM_PROVIDER=ollama` and `STT_PROVIDER=local`:
- Fully private, no internet required
- Uses Ollama (llama3.2:3b) for LLM
- Uses local faster-whisper for STT
- No web search capability

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

The default voice is **`en_GB-alan-medium`** — a refined British male voice similar to JARVIS from Iron Man. To use a multi-speaker voice instead:

1. Download `en_GB-vctk-medium` (109 speakers):
```bash
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/vctk/medium/en_GB-vctk-medium.onnx.json
```

2. Update `.env`:
```env
PIPER_VOICE=en_GB-vctk-medium
PIPER_SPEAKER=17  # 0-108, each speaker has a different voice
```

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

### Latency Breakdown

| Step | Groq (Cloud) | Ollama (Local) |
|------|-------------|----------------|
| STT transcription | ~0.5s | 1-2s |
| Query routing | ~0.2s | skipped |
| Web search (if needed) | ~2.5s | N/A |
| LLM first token | ~0.3s | 1-2s |
| TTS per sentence | 0.07s | 0.07s |
| **Total (no search)** | **~1.5s** | **~3-4s** |
| **Total (with search)** | **~4s** | **N/A** |

### Key Optimizations

✅ **Groq Cloud LLM** (llama-3.3-70b-versatile)
- 70B parameter model via cloud API
- Automatic fallback to local Ollama on rate limit (100K tokens/day free tier)
- Rate limit tracking: skips failed Groq calls instead of wasting roundtrips

✅ **LLM-Based Query Routing**
- Fast classifier (llama-3.1-8b-instant, ~200ms) decides search vs direct answer
- Context-aware query rewriting: "what about 2025?" → "US Open 2025 winner"
- Skipped entirely during Groq rate limit (avoids adding latency to Ollama path)

✅ **Web Search via Tavily API**
- Real-time search results injected into LLM context
- 3-result summary with AI-generated answer
- 5-second timeout to prevent blocking

✅ **Non-Blocking LLM Streaming**
- LLM generation runs on worker thread via `asyncio.Queue`
- Event loop stays responsive for WebSocket handshakes during slow Ollama fallback
- No UI freezing even when LLM is generating

✅ **In-Process Piper TTS**
- OLD: Subprocess call per sentence (1.794s each)
- NEW: In-process PiperVoice (0.070s each)
- **25.6× faster TTS!**

✅ **Concurrent TTS Streaming**
- Generate audio per sentence → Start playing immediately
- Audio starts while LLM is still generating text

✅ **Groq Cloud STT** (whisper-large-v3-turbo)
- Higher accuracy than local small model
- Automatic fallback to local faster-whisper on failure

## 📁 Project Structure

```
ai-assistant/
├── backend/
│   └── server.py                  # FastAPI WebSocket server (non-blocking streaming)
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
│   │   ├── stt.py                # STT: Groq cloud + local Whisper fallback
│   │   ├── llm.py                # LLM: Groq + Ollama fallback, query router
│   │   ├── tts.py                # Piper TTS (in-process)
│   │   ├── audio_utils.py        # Audio I/O
│   │   └── assistant.py          # CLI interface (legacy)
│   ├── tools/
│   │   └── web_search.py         # Tavily web search integration
│   └── interfaces/
│       └── cli.py                # Terminal interface
├── config/
│   └── settings.py               # Pydantic settings (.env loader)
├── models/
│   └── piper/                    # TTS voice models
├── tests/
│   ├── test_llm.py
│   ├── test_tts.py
│   ├── test_server_security.py
│   └── test_turn.py
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
- [x] Wake word detection ("Hey Jarvis")
- [x] Local wake word processing (no cloud)
- [x] Auto-start recording on wake word
- [x] In-process Piper TTS (25× faster, 0.07s/sentence)
- [x] Cancellable TTS tasks (Turn-based cancellation)
- [x] Security hardening (CORS lockdown, audio size cap, temp file cleanup)
- [x] Always-on wake word launcher with port-reuse detection
- [x] Groq cloud LLM integration (llama-3.3-70b-versatile)
- [x] Groq cloud STT (whisper-large-v3-turbo) with local fallback
- [x] JARVIS persona system prompt (Iron Man-inspired personality)
- [x] Web search tool via Tavily API
- [x] LLM-based query routing (search vs direct answer, context-aware rewriting)
- [x] Groq rate limit tracking with automatic Ollama fallback
- [x] Non-blocking LLM streaming (worker threads + asyncio.Queue)
- [x] Configurable idle auto-shutdown (env-based, client-aware)

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

- [Groq](https://groq.com) - Ultra-fast cloud LLM and STT inference
- [Tavily](https://tavily.com) - AI-optimized web search API
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Ollama](https://ollama.ai) - Local LLM hosting
- [Piper](https://github.com/rhasspy/piper) - Text-to-speech
- [openWakeWord](https://github.com/dscripka/openWakeWord) - Wake word detection
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Optimized local inference
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
