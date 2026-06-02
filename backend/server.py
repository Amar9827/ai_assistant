"""
WebSocket Backend Server for AI Voice Assistant

This server replaces the old CLI interface with a real-time WebSocket API
that streams responses word-by-word instead of waiting for the full response.

Key Changes from CLI:
1. FastAPI instead of CLI loop
2. WebSocket for bidirectional streaming
3. Async/await for concurrent operations
4. Real-time status updates (listening, processing, speaking)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import sys
import base64
import tempfile
from pathlib import Path
import uuid
from dataclasses import dataclass, field
from typing import Set

# Add parent directory to path to import from src/
sys.path.append(str(Path(__file__).parent.parent))

from src.core.llm import LLMProcessor
from src.core.stt import SpeechToText
from src.core.tts import TextToSpeech
from config.settings import Settings

# ============================================================
# Turn: Cancellable Task Primitive (Stage 2 prerequisite)
# ============================================================

@dataclass
class Turn:
    """One user→assistant exchange. Owns all in-flight tasks for that exchange.

    Stage 1: we create a Turn per query but never call cancel() on it.
    Stage 2: barge-in detection will call turn.cancel() the instant the user
    starts speaking, stopping pending TTS within ~50ms.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tasks: Set[asyncio.Task] = field(default_factory=set)
    _cancelled: bool = False

    def spawn(self, coro) -> asyncio.Task:
        """Run coro as a tracked task on this turn."""
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def cancel(self):
        """Cancel all in-flight tasks for this turn."""
        self._cancelled = True
        for t in list(self.tasks):
            if not t.done():
                t.cancel()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    async def wait_all(self):
        """Wait for all tracked tasks to complete (or be cancelled)."""
        if not self.tasks:
            return
        await asyncio.gather(*self.tasks, return_exceptions=True)

# Initialize FastAPI app
app = FastAPI(title="AI Voice Assistant", version="2.0")

# ============================================================
# Wake Word Integration
# ============================================================
# Track connected WebSocket clients for wake word broadcasting
active_websockets = set()
wake_word_enabled = True

# ============================================================
# Idle Auto-Shutdown (2 minutes)
# ============================================================
import time as _time
import os as _os
import signal as _signal

IDLE_TIMEOUT_SECONDS = 120  # 2 minutes
_last_activity_time = _time.time()
_idle_shutdown_task: asyncio.Task | None = None


def _touch_activity():
    """Reset the idle timer."""
    global _last_activity_time
    _last_activity_time = _time.time()


async def _idle_shutdown_watcher():
    """Background task: shuts down the server after IDLE_TIMEOUT_SECONDS of no activity."""
    while True:
        await asyncio.sleep(10)  # check every 10s
        idle_seconds = _time.time() - _last_activity_time
        if idle_seconds >= IDLE_TIMEOUT_SECONDS:
            print(f"[IDLE] No activity for {int(idle_seconds)}s — shutting down")
            # Close all WebSocket connections gracefully
            for ws in list(active_websockets):
                try:
                    await ws.close()
                except Exception:
                    pass
            await asyncio.sleep(0.5)
            _os._exit(0)

# Track whether the startup greeting has been played
_greeting_played = False


# Initialize AI components
settings = Settings()
llm = LLMProcessor(settings)
stt = SpeechToText(settings)
tts = TextToSpeech(settings)

# CORS middleware - allows frontend (localhost:5173) to connect
# Explanation: Without CORS, browsers block cross-origin requests
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM on startup (using modern lifespan pattern)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager - runs on startup and shutdown"""
    # Startup
    try:
        llm.initialize()
        print("[OK] Ollama connection verified")
    except Exception as e:
        print(f"[WARN] Could not connect to Ollama: {e}")
        print("       Make sure Ollama is running: ollama serve")

    try:
        stt.initialize()
        if stt.provider == "groq":
            print(f"[OK] STT: Groq cloud ({settings.GROQ_STT_MODEL}), fallback: local ({settings.WHISPER_MODEL})")
        else:
            print(f"[OK] STT: local faster-whisper ({settings.WHISPER_MODEL})")
    except Exception as e:
        print(f"[WARN] Could not load Whisper: {e}")

    try:
        tts.initialize()
        print("[OK] Piper TTS initialized")
    except Exception as e:
        print(f"[WARN] Could not initialize Piper: {e}")

    # Start idle shutdown watcher
    global _idle_shutdown_task
    _idle_shutdown_task = asyncio.create_task(_idle_shutdown_watcher())
    print(f"[OK] Idle auto-shutdown enabled ({IDLE_TIMEOUT_SECONDS}s)")

    yield

    # Shutdown (cleanup if needed)
    if _idle_shutdown_task:
        _idle_shutdown_task.cancel()
    print("[INFO] Server shutting down")

# Apply lifespan to app
app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    """Health check endpoint - verify server is running"""
    return {
        "status": "running",
        "version": "2.0",
        "websocket": "ws://localhost:8000/ws",
        "wake_word": "enabled" if wake_word_enabled else "disabled"
    }


@app.post("/wake-word/trigger")
async def wake_word_trigger():
    """
    Wake word detection trigger endpoint
    Called by external wake word service when 'Hey Jarvis' is detected
    Broadcasts to all connected WebSocket clients to start listening
    """
    _touch_activity()
    print("[WAKE WORD] Trigger received - broadcasting to clients...")

    # Broadcast wake word event to all connected clients
    disconnected = set()
    for ws in active_websockets:
        try:
            await ws.send_json({
                "type": "wake_word_detected",
                "wake_word": "Hey Jarvis"
            })
            print(f"[WAKE WORD] Notified client")
        except Exception as e:
            print(f"[WAKE WORD] Failed to notify client: {e}")
            disconnected.add(ws)

    # Remove disconnected clients
    active_websockets.difference_update(disconnected)

    return {
        "status": "triggered",
        "clients_notified": len(active_websockets) - len(disconnected)
    }


@app.get("/wake-word/status")
async def wake_word_status():
    """Check wake word integration status"""
    return {
        "enabled": wake_word_enabled,
        "connected_clients": len(active_websockets),
        "endpoint": "POST /wake-word/trigger"
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint - handles real-time bidirectional communication

    Message Types FROM frontend:
    - {"type": "start_listening"} - User clicked "Start Listening"
    - {"type": "stop_listening"} - User clicked "Stop"
    - {"type": "text_query", "text": "..."} - Text input (for testing)

    Message Types TO frontend:
    - {"type": "status", "status": "connected|listening|processing|speaking"}
    - {"type": "transcript", "text": "..."} - Streaming response text
    - {"type": "response", "user_query": "...", "response": "..."} - Final complete response
    - {"type": "audio_chunk", "audio": "base64..."} - Audio data (Step 5)
    """

    # Accept the WebSocket connection
    await websocket.accept()
    print("[WS] Frontend connected")

    # Add to active websockets for wake word broadcasting
    active_websockets.add(websocket)
    _touch_activity()
    print(f"[WS] Active connections: {len(active_websockets)}")

    try:
        # Send initial "connected" status
        await websocket.send_json({
            "type": "status",
            "status": "connected"
        })

        # Play startup greeting on first connection after server boot
        global _greeting_played
        if not _greeting_played:
            _greeting_played = True
            greeting = (
                "Systems initialized. Welcome back, Amar. "
                "What shall we tackle today, sir?"
            )
            try:
                greeting_turn = Turn()
                await websocket.send_json({"type": "status", "status": "speaking"})
                await websocket.send_json({
                    "type": "assistant_token",
                    "token": greeting,
                    "done": True,
                })
                await generate_and_stream_audio(websocket, greeting, greeting_turn)
                await websocket.send_json({"type": "audio_done"})
                await websocket.send_json({"type": "status", "status": "connected"})
                print("[JARVIS] Startup greeting played")
            except Exception as e:
                print(f"[JARVIS] Greeting failed: {e}")

        # Main message loop - wait for messages from frontend
        while True:
            # Receive message from frontend
            data = await websocket.receive_json()
            print(f"[<-] Received: {data.get('type')}")

            # Handle different message types
            if data["type"] == "start_listening":
                # Frontend started recording - just acknowledge
                await websocket.send_json({
                    "type": "status",
                    "status": "listening"
                })

            elif data["type"] == "audio_data":
                # Receive audio from frontend and transcribe
                _touch_activity()
                await handle_audio_data(websocket, data)

            elif data["type"] == "text_query":
                # Handle text-only query (useful for testing)
                _touch_activity()
                user_text = data.get("text", "")
                if user_text:
                    await handle_voice_query(websocket, user_text)

            elif data["type"] == "stop_listening":
                # User stopped recording
                await websocket.send_json({
                    "type": "status",
                    "status": "connected"
                })

    except WebSocketDisconnect:
        print("[WS] Frontend disconnected")
    except Exception as e:
        print(f"[ERROR] {e}")
        try:
            await websocket.send_json({
                "type": "status",
                "status": "error"
            })
        except:
            pass
    finally:
        # Remove from active websockets
        active_websockets.discard(websocket)
        print(f"[WS] Active connections: {len(active_websockets)}")


async def generate_and_stream_audio(websocket: WebSocket, text: str, turn: "Turn"):
    """Generate TTS for one sentence and stream chunks. Cancellable."""
    try:
        audio_array = await asyncio.to_thread(tts.synthesize, text)
        print(f"[TTS turn={turn.id}] Generated {len(audio_array)} samples")

        CHUNK_SIZE = 8192
        for i in range(0, len(audio_array), CHUNK_SIZE):
            if turn.cancelled:
                return
            chunk = audio_array[i:i + CHUNK_SIZE]
            chunk_base64 = base64.b64encode(chunk.tobytes()).decode()
            await websocket.send_json({
                "type": "audio_chunk",
                "audio": chunk_base64,
                "sample_rate": tts.last_sample_rate,
                "dtype": "int16",
            })
            await asyncio.sleep(0.02)
    except asyncio.CancelledError:
        print(f"[TTS turn={turn.id}] Cancelled mid-stream")
        raise
    except Exception as e:
        print(f"[TTS ERROR turn={turn.id}] {e}")


async def handle_audio_data(websocket: WebSocket, data: dict):
    """
    Handle audio data from frontend - transcribe and process

    Flow:
    1. Validate format and size
    2. Decode base64 audio
    3. Save to temporary file
    4. Transcribe with Whisper
    5. Process with LLM
    6. Delete temporary file

    Explanation:
    - Frontend sends audio as base64 string (WebSocket can't send binary directly in JSON)
    - We decode it back to binary and save as .webm file
    - Whisper transcribes the audio file
    - Then we process it like a text query
    """

    ALLOWED_FORMATS = {"webm", "wav", "ogg", "mp3"}
    tmp_path = None

    try:
        # Status: Processing (transcribing audio)
        await websocket.send_json({
            "type": "status",
            "status": "processing"
        })

        print("[<-] Received audio data")

        # Step 1: Validate format
        audio_format = data.get("format", "webm")
        if audio_format not in ALLOWED_FORMATS:
            print(f"[ERROR] Invalid audio format: {audio_format}")
            await websocket.send_json({
                "type": "status",
                "status": "error"
            })
            return

        # Step 2: Validate size
        audio_base64 = data.get("audio", "")
        if not audio_base64:
            print("[ERROR] No audio data received")
            return

        max_bytes = int(settings.MAX_AUDIO_MB) * 1024 * 1024
        if len(audio_base64) * 0.75 > max_bytes:
            print(f"[ERROR] Audio exceeds {settings.MAX_AUDIO_MB}MB limit")
            await websocket.send_json({
                "type": "status",
                "status": "error"
            })
            return

        # Step 3: Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)
        print(f"[AUDIO] Decoded {len(audio_bytes)} bytes")

        # Step 4: Save to temporary file
        # Explanation: Whisper expects a file path, not raw bytes
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            tmp_path = temp_audio.name
            print(f"[AUDIO] Saved to {tmp_path}")

        # Step 5: Transcribe with Whisper
        print("[STT] Transcribing audio...")
        user_text = await asyncio.to_thread(stt.transcribe_file, tmp_path)

        if not user_text or user_text.strip() == "":
            print("[STT] No speech detected in audio")
            await websocket.send_json({
                "type": "status",
                "status": "connected"
            })
            return

        print(f"[STT] Transcribed: {user_text}")

        # Step 6: Send transcribed text to frontend IMMEDIATELY
        # Explanation: Frontend needs to show user's message before assistant responds
        await websocket.send_json({
            "type": "user_transcript",
            "text": user_text
        })

        # Step 7: Process transcribed text with LLM
        await handle_voice_query(websocket, user_text)

    except Exception as e:
        print(f"[ERROR] Failed to process audio: {e}")
        import traceback
        traceback.print_exc()

        await websocket.send_json({
            "type": "status",
            "status": "error"
        })
    finally:
        # Clean up temporary file
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)
            print(f"[AUDIO] Deleted {tmp_path}")


async def handle_voice_query(websocket: WebSocket, user_text: str):
    """
    Process a query end-to-end. All TTS work runs as tasks on a Turn
    object so Stage 2 can cancel it for barge-in.
    """
    turn = Turn()
    try:
        await websocket.send_json({"type": "status", "status": "processing"})
        print(f"[USER turn={turn.id}] {user_text}")

        full_response = ""
        current_sentence = ""
        audio_started = False

        for chunk in llm.generate_response(user_text, stream=True):
            if turn.cancelled:
                break

            full_response += chunk
            current_sentence += chunk

            await websocket.send_json({"type": "transcript", "text": full_response})

            # Stage 1 keeps the original sentence detection. Stage 2 replaces
            # this entire block with continuous overlapping TTS via SentenceBuffer.
            if any(p in chunk for p in [". ", "! ", "? ", "\n"]):
                sentence = current_sentence.strip()
                if sentence:
                    if not audio_started:
                        await websocket.send_json({"type": "status", "status": "speaking"})
                        audio_started = True
                    # Spawn TTS as a tracked task; await it immediately for Stage 1.
                    # Stage 2 will let it run concurrently with the next iteration.
                    task = turn.spawn(generate_and_stream_audio(websocket, sentence, turn))
                    try:
                        await task
                    except asyncio.CancelledError:
                        break
                current_sentence = ""

            await asyncio.sleep(0.02)

        if current_sentence.strip() and not turn.cancelled:
            if not audio_started:
                await websocket.send_json({"type": "status", "status": "speaking"})
            task = turn.spawn(
                generate_and_stream_audio(websocket, current_sentence.strip(), turn)
            )
            try:
                await task
            except asyncio.CancelledError:
                pass

        print(f"[AI turn={turn.id}] {full_response}")

        if not turn.cancelled:
            await websocket.send_json({"type": "response", "response": full_response})
            await websocket.send_json({"type": "status", "status": "connected"})

    except Exception as e:
        print(f"[ERROR turn={turn.id}] {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "status", "status": "error"})
        except Exception:
            pass
    finally:
        # Ensure no orphan tasks survive the turn.
        turn.cancel()
        await turn.wait_all()


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("AI Voice Assistant Backend Server v2.0")
    print("=" * 60)
    print("WebSocket: ws://localhost:8000/ws")
    print("Health Check: http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print("=" * 60)
    print()

    # Run the server
    # host="0.0.0.0" means accept connections from any IP (including frontend)
    # reload=True will auto-restart on code changes (useful during development)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
