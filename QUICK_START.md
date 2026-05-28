# Quick Start Guide

## Start Everything (Easiest)

**Double-click:** `start_assistant.bat`

This opens 2 windows:
- Backend Server (port 8000)
- Wake Word Detection

Then open: `http://localhost:5173`

Say **"Hey Jarvis"** → Screen flashes → Recording starts!

## Stop Everything

**Double-click:** `stop_assistant.bat`

## Files You Need

```
ai-assistant/
├── start_assistant.bat     ← Double-click this to START
├── stop_assistant.bat      ← Double-click this to STOP
├── run_wake_word.py        ← Wake word service
├── backend/server.py       ← Backend server
└── wake_word_refs/         ← Your 3 "Hey Jarvis" samples
    ├── jarvis-2.wav
    ├── jarvis-3.wav
    └── jarvis-4.wav
```

## What Happens

1. You say **"Hey Jarvis"**
2. Screen flashes cyan
3. Recording starts automatically
4. You speak your command
5. Assistant responds

## Commands

```bash
# Start (2 windows)
start_assistant.bat

# Stop
stop_assistant.bat

# Start (1 window)
python run_all.py

# Test wake word only
python run_wake_word.py

# Re-record wake word
record_samples.bat
```

## Troubleshooting

**Wake word not detecting?**
→ Speak louder or run: `record_samples.bat`

**Port 8000 already in use?**
→ Run: `stop_assistant.bat`

**Frontend not connecting?**
→ Make sure backend is running first

## That's It!

🎤 Say "Hey Jarvis" and enjoy your hands-free AI assistant!

Full docs: `WAKE_WORD_COMPLETE.md`
