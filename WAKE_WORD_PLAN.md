# Wake Word Detection Implementation Plan

## Overview

Transform the assistant from command-triggered to always-listening mode with wake word activation (like "Hey Assistant").

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Background Service (Always Running)      │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  Continuous Audio Stream (Low CPU, 16kHz mono)  │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│   Wake Word Detection (Lightweight Model)       │
│   - Listen for "Hey Assistant" / custom phrase  │
│   - ~1-5% CPU usage                             │
└─────────────────────────────────────────────────┘
                     ↓ [Wake word detected]
┌─────────────────────────────────────────────────┐
│            Audio Feedback (Beep/Chime)          │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│   Full Query Recording (VAD with timeout)       │
│   - Record user's actual question               │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│   Existing Pipeline: Whisper → LLM → TTS        │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│        Return to Wake Word Listening Mode       │
└─────────────────────────────────────────────────┘
```

## Wake Word Detection Options

### Option 1: **Porcupine (Recommended)**
- **Pros**: Accurate, low latency (<30ms), cross-platform, custom wake words
- **Cons**: Requires API key (free tier: 3 wake words)
- **Resource**: ~2-5% CPU, ~10MB RAM
- **Library**: `pvporcupine`

### Option 2: **OpenWakeWord**
- **Pros**: 100% open source, no API key, custom training possible
- **Cons**: Slightly higher CPU usage, requires TensorFlow Lite
- **Resource**: ~5-10% CPU, ~50MB RAM
- **Library**: `openwakeword`

### Option 3: **Simple Keyword Spotting with Vosk**
- **Pros**: Fully offline, lightweight, integrates with Whisper
- **Cons**: Less accurate than dedicated wake word models
- **Resource**: ~10-15% CPU, ~100MB RAM
- **Library**: `vosk`

**Recommendation**: Start with **Porcupine** for accuracy, with OpenWakeWord as fallback for fully open source.

## Implementation Steps

### Phase 1: Wake Word Detection Core (Days 1-2)

#### 1.1 Add Dependencies
```python
# requirements.txt additions
pvporcupine>=2.2.0           # Wake word detection
soundfile>=0.12.0            # Audio file I/O
pyaudio>=0.2.13              # Alternative: already using sounddevice
```

#### 1.2 Create Wake Word Detector Module
**File**: `src/core/wake_word.py`

```python
class WakeWordDetector:
    def __init__(self, wake_words=['hey assistant'], sensitivity=0.5):
        """
        Initialize wake word detector
        
        Args:
            wake_words: List of wake words to detect
            sensitivity: 0.0-1.0, higher = more sensitive (more false positives)
        """
        
    def listen_for_wake_word(self) -> bool:
        """Continuously listen and return True when wake word detected"""
        
    def get_audio_stream(self):
        """Create optimized audio stream for wake word detection"""
```

#### 1.3 Audio Feedback System
**File**: `src/core/audio_feedback.py`

```python
class AudioFeedback:
    def play_activation_sound(self):
        """Play 'listening' chime when wake word detected"""
        
    def play_deactivation_sound(self):
        """Play 'done' sound after response"""
        
    def play_error_sound(self):
        """Play error beep if something fails"""
```

### Phase 2: Background Service Mode (Days 3-4)

#### 2.1 Create Daemon/Service Runner
**File**: `src/services/background_assistant.py`

```python
class BackgroundAssistant:
    def __init__(self):
        self.wake_detector = WakeWordDetector()
        self.assistant = VoiceAssistant()
        self.is_running = False
        
    def start(self):
        """Start background listening loop"""
        while self.is_running:
            # Listen for wake word
            if self.wake_detector.listen_for_wake_word():
                self.handle_activation()
                
    def handle_activation(self):
        """Called when wake word detected"""
        # 1. Play activation sound
        # 2. Record query with VAD
        # 3. Process through assistant
        # 4. Play deactivation sound
        # 5. Return to listening
        
    def stop(self):
        """Gracefully stop the service"""
```

#### 2.2 Add Service Control Interface
**File**: `src/interfaces/service_cli.py`

```python
# Commands:
# assistant-daemon start    - Start background service
# assistant-daemon stop     - Stop service
# assistant-daemon status   - Check if running
# assistant-daemon restart  - Restart service
```

#### 2.3 System Integration

**Windows**: Create Windows Service wrapper
```python
# install.bat additions
# Register as Windows startup service (optional)
```

**Linux/Mac**: Create systemd service
```bash
# /etc/systemd/system/ai-assistant.service
[Unit]
Description=AI Voice Assistant Background Service

[Service]
ExecStart=/path/to/venv/bin/python -m src.services.background_assistant
Restart=always

[Install]
WantedBy=multi-user.target
```

### Phase 3: Integration & Configuration (Day 5)

#### 3.1 Configuration Updates
**File**: `.env` additions

```env
# Wake Word Configuration
WAKE_WORD=hey assistant          # The phrase to detect
WAKE_WORD_SENSITIVITY=0.5        # 0.0-1.0, higher = more sensitive
WAKE_WORD_TIMEOUT=10             # Seconds to wait for query after wake word
WAKE_WORD_ENABLED=true           # Enable/disable wake word mode

# Background Service
RUN_AS_SERVICE=true              # Start as background service
PLAY_AUDIO_FEEDBACK=true         # Play activation/deactivation sounds
LOG_WAKE_DETECTIONS=false        # Log all wake word detections (debug)
```

#### 3.2 Update Main Assistant
**File**: `src/core/assistant.py`

Add new method:
```python
def process_voice_query_with_wake_word(self):
    """
    Process query after wake word detected
    - Assumes already activated
    - Shorter timeout (10s instead of 30s)
    - Returns to listening after response
    """
```

### Phase 4: Optimization & Testing (Day 6)

#### 4.1 Resource Optimization
- **CPU**: Keep wake word detection under 5% CPU
- **Memory**: Lazy load Whisper/LLM (only load when activated)
- **Battery**: Implement sleep mode after X minutes of inactivity

#### 4.2 Visual Feedback (Optional)
- System tray icon showing status (listening/processing/idle)
- Desktop notification when activated
- LED indicator if using Raspberry Pi

#### 4.3 Multi-User Support
- Voice profile recognition (optional advanced feature)
- Per-user wake words
- Conversation isolation

## File Structure After Implementation

```
ai-assistant/
├── src/
│   ├── core/
│   │   ├── wake_word.py          # NEW: Wake word detection
│   │   ├── audio_feedback.py     # NEW: Audio feedback (beeps/chimes)
│   │   └── assistant.py          # MODIFIED: Add wake word mode
│   ├── services/
│   │   ├── __init__.py           # NEW
│   │   └── background_assistant.py  # NEW: Background daemon
│   └── interfaces/
│       ├── service_cli.py        # NEW: Daemon control CLI
│       └── cli.py                # MODIFIED: Add wake word toggle
├── sounds/                        # NEW: Audio feedback files
│   ├── activation.wav
│   ├── deactivation.wav
│   └── error.wav
├── .env.example                   # MODIFIED: Add wake word config
└── README.md                      # MODIFIED: Document wake word usage
```

## Critical Considerations

### 1. **Privacy & Security**
- ✅ All processing still local (no cloud)
- ⚠️ Always-on microphone recording
- 💡 Add visual indicator when listening
- 💡 Hardware mute switch recommended

### 2. **Performance**
- Wake word detection: ~5% CPU
- Full assistant: ~40-60% CPU during processing
- **Solution**: Load Whisper/LLM only after wake word detected

### 3. **False Positives**
- Similar-sounding phrases trigger accidentally
- **Solution**: Adjust sensitivity, add confirmation sound
- **Solution**: 2-second timeout to cancel accidental triggers

### 4. **Audio Device Conflicts**
- Can't use mic while assistant is listening
- **Solution**: Release mic after each query
- **Solution**: Push-to-mute hotkey

### 5. **Startup Behavior**
- Should it auto-start on system boot?
- **Solution**: Make it configurable, default OFF

## Testing Plan

### Unit Tests
- Wake word detection accuracy (true/false positives)
- Audio feedback playback
- Service start/stop/restart
- Configuration loading

### Integration Tests
1. **Basic Flow**: Say wake word → query → response → return to listening
2. **False Positive**: Similar phrase doesn't trigger
3. **Multiple Queries**: Chain multiple queries in succession
4. **Interruption**: Stop service while processing
5. **Resource Leak**: Run for 24 hours, check memory/CPU

### Performance Benchmarks
| Metric | Target | Acceptable |
|--------|--------|------------|
| Wake word latency | <50ms | <100ms |
| False positive rate | <1/hour | <5/hour |
| CPU (idle listening) | <5% | <10% |
| Memory (idle) | <100MB | <200MB |
| Battery impact | <5%/hour | <10%/hour |

## Example Usage

### As Background Service
```bash
# Start service
assistant-daemon start

# Status check
assistant-daemon status
# Output: AI Assistant is listening for "Hey Assistant"...

# User speaks: "Hey Assistant"
# [Chime sound] 🔊
# User: "What's the weather today?"
# Assistant: "I don't have real-time weather data..."
# [Done sound] 🔊
# [Returns to listening]

# Stop service
assistant-daemon stop
```

### Manual Mode (Existing)
```bash
# Traditional CLI mode still available
assistant-cli
Choose mode [voice/text/reset/quit] (voice):
```

## Rollout Strategy

### Week 1: MVP
- Porcupine wake word detection
- Basic activation → query → response flow
- Manual daemon start/stop

### Week 2: Polish
- Audio feedback sounds
- System service integration (Windows/Linux)
- Configuration UI

### Week 3: Advanced
- Custom wake word training
- Voice profiles (optional)
- System tray app

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| High false positives | User frustration | Adjustable sensitivity, confirmation sound |
| Battery drain on laptops | Limited portability | Sleep mode, auto-pause when idle |
| Conflicts with other voice assistants | Both trigger | Different wake words, explicit disable |
| Privacy concerns | User distrust | Clear visual indicator, easy disable, local-only |

## Questions to Answer

1. **Wake word phrase**: "Hey Assistant"? "Computer"? Custom?
2. **Auto-start**: Should it start on system boot?
3. **Visual feedback**: System tray icon? Desktop notification?
4. **Timeout**: How long to wait for query after wake word (10s default)?
5. **Sensitivity**: Prefer false positives or false negatives?

---

## Implementation Status

- [ ] Phase 1: Wake Word Detection Core
- [ ] Phase 2: Background Service Mode
- [ ] Phase 3: Integration & Configuration
- [ ] Phase 4: Optimization & Testing

---

# APPENDIX: Async Architecture Refactor (Pre-requisite)

## Overview

Based on analysis of [ADA V2 repository](https://github.com/nazirlouis/ada_v2), we should refactor to an async architecture BEFORE implementing wake word detection. This enables natural interruption handling and better resource utilization while maintaining 100% local operation.

**Reference**: See `ADA_INTEGRATION_ANALYSIS.md` for detailed comparison.

## Why Async First?

Wake word detection requires:
- Continuous background listening (async task)
- Ability to interrupt current response when new wake word detected
- Efficient resource sharing between wake word monitor and full assistant

Current synchronous architecture blocks during processing - incompatible with always-on listening.

## Async Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                   AsyncVoiceAssistant                        │
│  (Main event loop coordinating concurrent tasks)             │
└─────────────────────────────────────────────────────────────┘
         │
         ├──────────────┬──────────────┬──────────────┬─────────────
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐
│ Listen Task  │ │ Process Task │ │ Speak Task   │ │ Monitor Task│
│              │ │              │ │              │ │             │
│ Continuous   │ │ Query Queue  │ │ Response     │ │ Interrupt   │
│ VAD          │ │ → Whisper    │ │ Queue        │ │ Detection   │
│ recording    │ │ → LLM stream │ │ → TTS        │ │             │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                   asyncio.Queue communication
```

## Implementation Plan

### Step 1: Core Async Components (1 day)

**File**: `src/core/async_assistant.py`

```python
import asyncio
from typing import Optional

class AsyncVoiceAssistant:
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Queues for inter-task communication
        self.query_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        
        # State management
        self.is_speaking = asyncio.Event()
        self.interrupt_requested = asyncio.Event()
        
        # Components (lazy loaded)
        self.stt = None
        self.llm = None
        self.tts = None
        
    async def initialize(self):
        """Async initialization of components"""
        self.stt = SpeechToText(self.settings)
        self.llm = LLMProcessor(self.settings)
        self.tts = TextToSpeech(self.settings)
        
        await asyncio.gather(
            asyncio.to_thread(self.stt.initialize),
            asyncio.to_thread(self.llm.initialize),
            asyncio.to_thread(self.tts.initialize)
        )
        
    async def run(self):
        """Main event loop"""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.listen_continuous())
            tg.create_task(self.process_queries())
            tg.create_task(self.speak_responses())
            tg.create_task(self.monitor_interruptions())
            
    async def listen_continuous(self):
        """Continuously record with VAD"""
        while True:
            audio = await asyncio.to_thread(
                self.recorder.record_with_vad
            )
            if len(audio) > 0:
                await self.query_queue.put(audio)
                
    async def process_queries(self):
        """Process recorded queries"""
        while True:
            audio = await self.query_queue.get()
            
            # Transcribe
            text = await asyncio.to_thread(
                self.stt.transcribe, audio
            )
            
            # Stream LLM response
            async for sentence in self._stream_llm_async(text):
                if self.interrupt_requested.is_set():
                    break  # User interrupted
                await self.response_queue.put(sentence)
                
            self.query_queue.task_done()
            
    async def speak_responses(self):
        """Play TTS responses"""
        while True:
            sentence = await self.response_queue.get()
            
            self.is_speaking.set()
            
            # Check for interrupt while speaking
            try:
                audio = await asyncio.to_thread(
                    self.tts.synthesize, sentence
                )
                await self._play_interruptible(audio)
            except InterruptedError:
                print("Response interrupted by user")
                
            self.is_speaking.clear()
            self.response_queue.task_done()
            
    async def monitor_interruptions(self):
        """Detect user speaking during response"""
        while True:
            if self.is_speaking.is_set():
                # Monitor for new speech
                if await self._detect_user_speech():
                    self.interrupt_requested.set()
                    self._clear_queues()
                    
            await asyncio.sleep(0.1)
            
    async def _stream_llm_async(self, text: str):
        """Async wrapper for LLM streaming"""
        for sentence in self.llm.generate_streaming_sentences(text):
            if self.interrupt_requested.is_set():
                break
            yield sentence
            
    async def _play_interruptible(self, audio):
        """Play audio but allow interruption"""
        # Implementation: play in chunks, check interrupt flag
        # between chunks
        pass
        
    def _clear_queues(self):
        """Clear pending responses on interrupt"""
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
```

### Step 2: Async Audio Utils (0.5 days)

**File**: `src/core/async_audio_utils.py`

```python
class AsyncAudioRecorder:
    async def record_with_vad_async(self, ...):
        """Async VAD recording"""
        return await asyncio.to_thread(
            self.record_with_vad, ...
        )
        
class AsyncAudioPlayer:
    async def play_async(self, audio_data, sample_rate):
        """Async audio playback"""
        await asyncio.to_thread(
            self.play, audio_data, sample_rate
        )
        
    async def play_interruptible(self, audio_data, sample_rate, interrupt_event):
        """Play audio in chunks, check interrupt flag"""
        CHUNK_SIZE = 4096
        for i in range(0, len(audio_data), CHUNK_SIZE):
            if interrupt_event.is_set():
                raise InterruptedError()
            chunk = audio_data[i:i+CHUNK_SIZE]
            await asyncio.to_thread(
                sd.play, chunk, sample_rate
            )
            await asyncio.sleep(0.01)
```

### Step 3: Update CLI Interface (0.5 days)

**File**: `src/interfaces/async_cli.py`

```python
class AsyncCLIInterface:
    def __init__(self):
        self.console = Console()
        self.assistant = AsyncVoiceAssistant()
        
    async def run(self):
        """Async CLI loop"""
        self.console.print(Panel.fit(
            "[bold green]🎤 Local AI Voice Assistant (Async Mode)[/bold green]\n"
            "Features: Interruption support, concurrent processing\n\n"
            "Commands: 'start', 'stop', 'status', 'quit'",
            border_style="green"
        ))
        
        await self.assistant.initialize()
        
        # Start assistant in background
        assistant_task = asyncio.create_task(self.assistant.run())
        
        # User control loop
        while True:
            command = await asyncio.to_thread(
                Prompt.ask,
                "[cyan]Command[/cyan]",
                choices=["start", "stop", "status", "quit"],
                default="start"
            )
            
            if command == "quit":
                assistant_task.cancel()
                break
            # ... handle other commands
                
def main():
    asyncio.run(AsyncCLIInterface().run())
```

### Step 4: Testing & Validation (0.5 days)

**Test Cases:**
1. ✅ Multiple queries in quick succession
2. ✅ Interrupt mid-response with new query
3. ✅ Queue clearing works correctly
4. ✅ No memory leaks over 1 hour
5. ✅ CPU usage acceptable during idle

## Benefits Over Current Architecture

| Feature | Current (Sync) | Async Refactor |
|---------|----------------|----------------|
| **Concurrent Processing** | Sequential only | Full concurrency ✅ |
| **Interruption** | Not possible ❌ | Natural ✅ |
| **Resource Efficiency** | Blocking waits | Event-driven ✅ |
| **Wake Word Ready** | No ❌ | Yes ✅ |
| **Queue Management** | N/A | Built-in ✅ |
| **Responsiveness** | Good | Excellent ✅ |

## Migration Path

### Phase 1: Parallel Implementation
- Keep existing `assistant.py` working
- Build `async_assistant.py` alongside
- Add `--async` flag to CLI for testing

### Phase 2: Gradual Migration
- Port CLI to async first
- Then web interface
- Finally GUI

### Phase 3: Deprecation
- Mark sync version as deprecated
- Remove after 2-week transition period

## Integration with Wake Word

Once async architecture is in place:

```python
class AsyncVoiceAssistant:
    async def run(self):
        async with asyncio.TaskGroup() as tg:
            # NEW: Wake word detection task
            tg.create_task(self.detect_wake_word())
            
            tg.create_task(self.listen_continuous())
            tg.create_task(self.process_queries())
            tg.create_task(self.speak_responses())
            tg.create_task(self.monitor_interruptions())
            
    async def detect_wake_word(self):
        """Continuously listen for wake word"""
        while True:
            if await self.wake_detector.listen():
                # Wake word detected!
                await self.audio_feedback.play_activation()
                self.listening_enabled.set()
```

## Timeline

**Total Estimated Time**: 2-3 days

| Step | Duration | Priority |
|------|----------|----------|
| Core async components | 1 day | Critical |
| Async audio utils | 0.5 days | Critical |
| CLI update | 0.5 days | High |
| Testing & validation | 0.5 days | Critical |
| Documentation | 0.5 days | Medium |

## Decision

**Recommendation**: Implement async refactor BEFORE wake word detection.

**Reason**: 
1. Wake word requires async architecture anyway
2. Improves current UX immediately (interruption support)
3. Better foundation for future features
4. Maintains 100% local operation

---

## Notes

Created: 2026-05-23
Updated: 2026-05-23
Status: Planning Phase
Priority: High (Async Refactor) → High (Wake Word Detection)
Estimated Time: 
  - Async Refactor: 2-3 days
  - Wake Word: 1-2 weeks (after async)
  - **Total**: ~2-3 weeks
