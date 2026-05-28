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
                    ┌───────────▼────────────┐
                    │ Wake Word Service      │
                    │ (run_wake_word.py)     │
                    │ - local-wake library   │
                    │ - Google embeddings    │
                    │ - DTW matching         │
                    │ - Debounced detection  │
                    └────────────────────────┘
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

**6. Record wake word samples (optional - for "Hey Jarvis"):**
```bash
# Record 3 voice samples of "Hey Jarvis"
python record_wake_word.py

# This creates wake_word_refs/ directory with your voice samples
# Skip this if you don't want wake word activation
```

### Running the Assistant

#### Option 1: Quick Start (Windows) - With Wake Word
```bash
# Start everything at once
start_assistant.bat

# This opens two windows:
# 1. Backend server (port 8000) + Wake word detector
# 2. Frontend dev server (port 5173)

# To stop:
stop_assistant.bat
```

#### Option 2: Manual Start (All Platforms)

**Terminal 1 - Start Backend:**
```bash
cd ai_assistant
python backend/server.py
# Backend runs on http://localhost:8000
```

**Terminal 2 - Start Wake Word Service (optional):**
```bash
cd ai_assistant
python run_wake_word.py
# Listens for "Hey Jarvis" and triggers recording automatically
```

**Terminal 3 - Start Frontend:**
```bash
cd ai_assistant/frontend
npm run dev
# Frontend runs on http://localhost:5173
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

**Note:** Wake word service must be running (`run_wake_word.py` or `start_assistant.bat`)

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
- **Debounced Detection**: 2-second cooldown prevents multiple triggers

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

# Wake Word Detection
WAKE_WORD_THRESHOLD=0.22         # Lower = more sensitive (0.15-0.30 recommended)
WAKE_WORD_DEBOUNCE=2.0           # Seconds between detections

# Audio Settings
SAMPLE_RATE=16000
```

### Wake Word Configuration

The wake word detector uses **local-wake** library with custom voice samples:

**Sensitivity Tuning (`WAKE_WORD_THRESHOLD`):**
- **0.15-0.20**: Very sensitive (may have false positives)
- **0.22** ⭐: Balanced (recommended - 100% accuracy in testing)
- **0.25-0.30**: Less sensitive (may miss some attempts)

**Recording Your Voice:**
```bash
# Record 3 samples of "Hey Jarvis"
python record_wake_word.py

# Test detection accuracy
python run_wake_word.py
# Say "Hey Jarvis" and watch console output
```

**How it works:**
- Uses Google's speech embedding model (local inference via ONNX)
- Dynamic Time Warping (DTW) matches your voice to recorded samples
- 2-second debounce prevents multiple triggers from one utterance
- ~50ms detection latency (nearly instant)

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
| **Time to first audio** | **1.5s** | **Concurrent TTS** ⚡ |
| Complete response | 5-8s | Depends on length |

### Key Optimizations

✅ **Concurrent TTS Streaming**
- OLD: Wait for full text (5s) → Generate all audio (2s) → Play (7s total)
- NEW: Generate audio per sentence → Start playing immediately (1.5s)
- **79% faster perceived latency!**

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
│   ├── server.py                  # FastAPI WebSocket server
│   └── wake_word_local.py         # Wake word detector class
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
├── wake_word_refs/               # Your recorded wake word samples
│   ├── jarvis-2.wav
│   ├── jarvis-3.wav
│   └── jarvis-4.wav
├── run_wake_word.py              # Wake word service (standalone)
├── record_wake_word.py           # Tool to record wake word samples
├── start_assistant.bat           # Windows: Start all services
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
# Test wake word service alone
python run_wake_word.py
# Say "Hey Jarvis" clearly - should see console output

# Check threshold setting
# Edit backend/wake_word_local.py: threshold=0.22 (try 0.20-0.25)

# Re-record samples if still not working
python record_wake_word.py
```

**Wake word too sensitive (false positives):**
- Increase threshold: `threshold=0.25` in `backend/wake_word_local.py`
- Ensure background is quiet during sample recording
- Record samples in the same environment where you'll use it

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
- [x] **Wake word detection ("Hey Jarvis")** 🆕
- [x] **Local wake word processing (no cloud)** 🆕
- [x] **Auto-start recording on wake word** 🆕

### In Progress 🚧
- [ ] Atomic LLM history commits (prevent corruption)
- [ ] In-process Piper TTS (eliminate subprocess overhead)
- [ ] Cancellable TTS tasks (interrupt mid-response)
- [ ] Security hardening (CORS, rate limiting, input validation)

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
- [local-wake](https://github.com/st-matskevich/local-wake) - Wake word detection
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference
- [FastAPI](https://fastapi.tiangolo.com/) - WebSocket backend
- [React](https://react.dev/) - Modern UI framework
- [Vite](https://vitejs.dev/) - Fast build tool

## 📚 Documentation

- [STAGE1_CRITICAL_FIXES.md](STAGE1_CRITICAL_FIXES.md) - Critical improvements in progress
- [JARVIS_UI_REDESIGN_PLAN.md](JARVIS_UI_REDESIGN_PLAN.md) - Futuristic UI redesign plan
- [BASELINE.txt](BASELINE.txt) - System baseline measurements
- Architecture diagrams in README (see above)

## 💬 Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/Amar9827/ai_assistant/issues)
- Check [Troubleshooting](#-troubleshooting) section above

---

**Made with ❤️ for local AI enthusiasts**

*Privacy-first • Lightning-fast • Always yours*
