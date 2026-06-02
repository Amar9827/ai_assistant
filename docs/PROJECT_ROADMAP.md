# JARVIS AI Assistant — Project Roadmap

## Current State (Completed)

- [x] Wake word detection (openWakeWord, "Hey Jarvis")
- [x] STT: Groq cloud Whisper large-v3-turbo + local faster-whisper fallback
- [x] LLM: Groq cloud llama-3.3-70b + Ollama local fallback
- [x] Streaming WebSocket responses (word-by-word)
- [x] Piper TTS: en_GB-alan-medium voice (JARVIS-like), 0.85x speed
- [x] Always-on wake word launcher with auto server lifecycle
- [x] Idle auto-shutdown (2 min timeout)
- [x] React frontend with audio visualizer
- [x] Turn infrastructure (cancellable tasks, Stage 2 ready)
- [x] 21 passing tests

---

## Phase 1 — Core Intelligence

High impact, moderate effort. Makes JARVIS significantly smarter.

### 1.1 Web Search Tool
- **Priority:** High
- **Description:** Give the LLM the ability to search the web for real-time information (weather, news, facts, prices).
- **Approach:** Use Groq function-calling API. LLM decides when to search. Integrate Brave Search or Tavily API.
- **Files:** `src/core/llm.py`, new `src/tools/web_search.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — web_search tool

### 1.2 Conversation Memory (Persistent)
- **Priority:** High
- **Description:** Persist conversation history to disk so context survives server restarts.
- **Approach:** Save/load JSON history file. Auto-trim to MAX_HISTORY_TURNS. Load on startup.
- **Files:** `src/core/llm.py`, `config/settings.py`

### 1.3 JARVIS System Prompt Persona
- **Priority:** Medium
- **Description:** Replace generic "helpful voice assistant" prompt with a JARVIS-specific persona — formal British butler, addresses user as "sir", proactive, witty.
- **Approach:** Dedicated system prompt file or config constant. Tuned for voice output (concise, natural phrasing).
- **Files:** `src/core/llm.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — JARVIS_SYSTEM_PROMPT.md

### 1.4 Barge-In / Interrupt
- **Priority:** Medium
- **Description:** Stop TTS playback mid-sentence when user starts speaking again. Provides natural conversational flow.
- **Approach:** Turn.cancel() infrastructure already exists. Frontend detects mic input during playback → sends cancel signal → backend cancels current Turn's tasks.
- **Files:** `backend/server.py`, `frontend/src/App.jsx`

---

## Phase 2 — System Integration

Medium impact, medium effort. Gives JARVIS hands to interact with the system.

### 2.1 App Launcher
- **Priority:** Medium
- **Description:** Voice commands to open applications: "Open Chrome", "Launch VS Code", "Open File Explorer".
- **Approach:** LLM tool-calling with a safe app-launch function. Whitelist of allowed apps or pattern matching.
- **Files:** New `src/tools/app_launcher.py`
- **Reference:** [novik133/jarvis](https://github.com/novik133/jarvis) — voice command mappings, [cgtarmenta/jarvis](https://github.com/cgtarmenta/jarvis) — spec 0015 voice-driven app launcher

### 2.2 Shell Command Execution
- **Priority:** Medium
- **Description:** LLM can run safe shell commands: "What's my IP?", "How much disk space do I have?", "What processes are using the most memory?"
- **Approach:** Sandboxed execution — read-only commands only, timeout limits, output truncation. LLM decides when to use.
- **Security:** Command whitelist/blocklist. No destructive commands (rm, del, format). Output sanitized before LLM sees it.
- **Files:** New `src/tools/shell.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — bash_exec tool

### 2.3 Date/Time/Timers
- **Priority:** Low
- **Description:** Built-in tools for current time, date, and simple countdown timers. No web search needed.
- **Approach:** Python `datetime` + `asyncio.sleep` for timers. TTS announces when timer expires.
- **Files:** New `src/tools/datetime_tools.py`, `backend/server.py`
- **Reference:** [novik133/jarvis](https://github.com/novik133/jarvis) — timer presets and custom timers

### 2.4 File Operations
- **Priority:** Low
- **Description:** Read, write, and create files via voice: "Create a note on my desktop called meeting notes".
- **Approach:** LLM tool-calling with file read/write functions. Restricted to safe directories (Desktop, Documents).
- **Security:** Path traversal prevention. No access outside allowed directories.
- **Files:** New `src/tools/file_ops.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — file_ops tool

---

## Phase 3 — UI/UX Polish

High visual impact. Makes JARVIS look and feel like Iron Man.

### 3.1 Iron Man HUD Redesign
- **Priority:** High
- **Description:** Full UI overhaul with Iron Man aesthetic — dark background, cyan/blue accents, arc reactor animation, holographic elements.
- **Approach:** CSS overhaul + new React components. Arc reactor as central visualizer. Glass-morphism panels.
- **Files:** `frontend/src/App.css`, `frontend/src/components/`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — full HUD with arc reactor + thinking stream + task tracker, [novik133/jarvis](https://github.com/novik133/jarvis) — waveform visualizer + holographic UI

### 3.2 Thinking/Speaking Indicators
- **Priority:** Medium
- **Description:** Show LLM "thinking" activity separately from the spoken response. Visual feedback during processing.
- **Approach:** Distinct UI zones: thinking indicator (shimmer/pulse), streaming text, and audio waveform.
- **Files:** `frontend/src/components/`, `backend/server.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — live thinking stream panel

### 3.3 Model Selector in UI
- **Priority:** Low
- **Description:** Switch between Groq models (llama-3.3-70b, llama-3.1-8b) or toggle to Ollama from the frontend header.
- **Approach:** Dropdown in UI header → WebSocket message to backend → update LLM config live.
- **Files:** `frontend/src/components/`, `backend/server.py`, `src/core/llm.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — header model selector

### 3.4 Abort Button
- **Priority:** Medium
- **Description:** Cancel button in UI to stop current LLM response and TTS playback immediately.
- **Approach:** Frontend sends cancel message → backend calls Turn.cancel() → all in-flight tasks stopped.
- **Files:** `frontend/src/App.jsx`, `backend/server.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — ABORT button

---

## Phase 4 — Reliability & Polish

Low risk, high quality. Makes JARVIS feel production-grade.

### 4.1 VAD (Voice Activity Detection)
- **Priority:** High
- **Description:** Use webrtcvad or silero-vad to detect when user stops speaking, instead of fixed recording duration. Reduces latency — transcription starts the moment user finishes.
- **Approach:** Frontend streams audio continuously; VAD detects speech end → triggers transcription.
- **Files:** `frontend/src/App.jsx`, `backend/server.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — webrtcvad integration

### 4.2 Notification Sounds
- **Priority:** Low
- **Description:** Audio chimes for wake word detection (activation beep), ready state, and errors.
- **Approach:** Short WAV files played via Web Audio API on specific events.
- **Files:** `frontend/src/App.jsx`, new `frontend/public/sounds/`
- **Reference:** [novik133/jarvis](https://github.com/novik133/jarvis) — audio alerts

### 4.3 Graceful Error Messages (Spoken)
- **Priority:** Medium
- **Description:** Speak errors via TTS instead of silent failures: "I'm sorry sir, I couldn't reach the server" or "I didn't catch that, could you repeat?"
- **Approach:** Backend catches errors → sends TTS-friendly error text → frontend plays it.
- **Files:** `backend/server.py`
- **Reference:** [cgtarmenta/jarvis](https://github.com/cgtarmenta/jarvis) — voiced error handling

### 4.4 Health Check Endpoint
- **Priority:** Low
- **Description:** `/healthz` endpoint showing backend status, active provider (Groq/Ollama), STT provider, model names, uptime, conversation length.
- **Approach:** Simple FastAPI GET endpoint returning JSON status.
- **Files:** `backend/server.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — `/healthz` with backend + credentials state

---

## Phase 5 — Advanced (Stretch Goals)

Ambitious features for a fully-featured assistant.

### 5.1 Persistent Memory
- **Priority:** Medium
- **Description:** Long-term memory store — JARVIS remembers user preferences, past facts, and context across sessions. "Remember that my wife's birthday is March 15th."
- **Approach:** Key-value store or vector DB (ChromaDB). LLM tool to save/recall memories.
- **Files:** New `src/tools/memory.py`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — memory tool

### 5.2 Multi-Language Support
- **Priority:** Low
- **Description:** Switch TTS voice and STT language via config or voice command. Support English, Spanish, etc.
- **Approach:** Multiple Piper voices per language. Groq Whisper supports 50+ languages. Config toggle.
- **Files:** `config/settings.py`, `src/core/stt.py`, `src/core/tts.py`
- **Reference:** [cgtarmenta/jarvis](https://github.com/cgtarmenta/jarvis) — language auto-detection from $LANG

### 5.3 Timers & Reminders
- **Priority:** Low
- **Description:** "Set a timer for 5 minutes", "Remind me at 3pm to call John". Timer expires → TTS announcement.
- **Approach:** asyncio-based timer queue. Persisted to disk for crash recovery.
- **Files:** New `src/tools/reminders.py`, `backend/server.py`
- **Reference:** [novik133/jarvis](https://github.com/novik133/jarvis) — quick presets and custom timers

### 5.4 System Monitor
- **Priority:** Low
- **Description:** Real-time CPU, RAM, disk, and temperature display in the HUD. Ask "How's the system doing?"
- **Approach:** `psutil` for metrics. WebSocket stream to frontend. Dashboard panel in UI.
- **Files:** New `src/tools/system_monitor.py`, `frontend/src/components/SystemMonitor.jsx`
- **Reference:** [novik133/jarvis](https://github.com/novik133/jarvis) — real-time system monitor panel

### 5.5 MCP Server Integration
- **Priority:** Low
- **Description:** Connect to external Model Context Protocol servers for extensibility — GitHub, smart home, custom APIs.
- **Approach:** MCP client in backend. Config file to list external servers. Tools auto-discovered.
- **Files:** New `src/core/mcp_client.py`, `config/mcp.json`
- **Reference:** [EliseyRotar/jarvis-ai](https://github.com/EliseyRotar/jarvis-ai) — mcp.json.example for external MCP servers

---

## Architecture Reference

```
Wake Word (openWakeWord) ─► Auto-launch backend + frontend
                                    │
                              STT (Groq cloud / local Whisper)
                                    │
                              LLM (Groq 70B / Ollama fallback)
                               │         │
                          [Tools]    Streaming WebSocket
                          - web_search    │
                          - shell         ▼
                          - app_launch  React HUD ─► Piper TTS ─► Speakers
                          - file_ops
                          - memory
                          - timers
```

---

*Last updated: June 2, 2026*
