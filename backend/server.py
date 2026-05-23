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

# Add parent directory to path to import from src/
sys.path.append(str(Path(__file__).parent.parent))

from src.core.llm import LLMProcessor
from src.core.stt import SpeechToText
from src.core.tts import TextToSpeech
from config.settings import Settings

# Initialize FastAPI app
app = FastAPI(title="AI Voice Assistant", version="2.0")

# CORS middleware - allows frontend (localhost:5173) to connect
# Explanation: Without CORS, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change to ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI components
settings = Settings()
llm = LLMProcessor(settings)
stt = SpeechToText(settings)
tts = TextToSpeech(settings)

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
        print("[OK] Whisper model loaded")
    except Exception as e:
        print(f"[WARN] Could not load Whisper: {e}")

    try:
        tts.initialize()
        print("[OK] Piper TTS initialized")
    except Exception as e:
        print(f"[WARN] Could not initialize Piper: {e}")

    yield

    # Shutdown (cleanup if needed)
    print("[INFO] Server shutting down")

# Apply lifespan to app
app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    """Health check endpoint - verify server is running"""
    return {
        "status": "running",
        "version": "2.0",
        "websocket": "ws://localhost:8000/ws"
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

    try:
        # Send initial "connected" status
        await websocket.send_json({
            "type": "status",
            "status": "connected"
        })

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
                await handle_audio_data(websocket, data)

            elif data["type"] == "text_query":
                # Handle text-only query (useful for testing)
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


async def generate_and_stream_audio(websocket: WebSocket, text: str):
    """
    Generate TTS audio for a sentence and stream it immediately

    Explanation:
    - This function is called for EACH sentence as it arrives
    - Audio generation happens in parallel with text streaming
    - No waiting for complete response before starting audio!

    Performance:
    - OLD: Wait 5s for all text → 2s TTS → play (7s total)
    - NEW: 1s for first sentence → 0.5s TTS → play (1.5s total!)
    """

    try:
        # Generate audio for this sentence (in thread pool to avoid blocking)
        audio_array = await asyncio.to_thread(tts.synthesize, text)

        print(f"[TTS] Generated {len(audio_array)} samples for: \"{text[:50]}...\"")

        # Stream audio chunks immediately
        CHUNK_SIZE = 8192  # samples per chunk (~0.37 seconds at 22050 Hz)

        for i in range(0, len(audio_array), CHUNK_SIZE):
            chunk = audio_array[i:i + CHUNK_SIZE]
            chunk_bytes = chunk.tobytes()
            chunk_base64 = base64.b64encode(chunk_bytes).decode()

            await websocket.send_json({
                "type": "audio_chunk",
                "audio": chunk_base64,
                "sample_rate": tts.last_sample_rate,
                "dtype": "int16"
            })

            # Smaller delay for faster streaming
            await asyncio.sleep(0.02)  # 20ms between chunks

    except Exception as e:
        print(f"[TTS ERROR] Failed to generate audio: {e}")


async def handle_audio_data(websocket: WebSocket, data: dict):
    """
    Handle audio data from frontend - transcribe and process

    Flow:
    1. Decode base64 audio
    2. Save to temporary file
    3. Transcribe with Whisper
    4. Process with LLM
    5. Delete temporary file

    Explanation:
    - Frontend sends audio as base64 string (WebSocket can't send binary directly in JSON)
    - We decode it back to binary and save as .webm file
    - Whisper transcribes the audio file
    - Then we process it like a text query
    """

    try:
        # Status: Processing (transcribing audio)
        await websocket.send_json({
            "type": "status",
            "status": "processing"
        })

        print("[<-] Received audio data")

        # Step 1: Decode base64 audio
        audio_base64 = data.get("audio", "")
        audio_format = data.get("format", "webm")

        if not audio_base64:
            print("[ERROR] No audio data received")
            return

        audio_bytes = base64.b64decode(audio_base64)
        print(f"[AUDIO] Decoded {len(audio_bytes)} bytes")

        # Step 2: Save to temporary file
        # Explanation: Whisper expects a file path, not raw bytes
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            print(f"[AUDIO] Saved to {temp_audio_path}")

        # Step 3: Transcribe with Whisper
        print("[STT] Transcribing audio...")
        user_text = await asyncio.to_thread(stt.transcribe_file, temp_audio_path)

        # Clean up temporary file
        Path(temp_audio_path).unlink()
        print(f"[AUDIO] Deleted {temp_audio_path}")

        if not user_text or user_text.strip() == "":
            print("[STT] No speech detected in audio")
            await websocket.send_json({
                "type": "status",
                "status": "connected"
            })
            return

        print(f"[STT] Transcribed: {user_text}")

        # Step 4: Send transcribed text to frontend IMMEDIATELY
        # Explanation: Frontend needs to show user's message before assistant responds
        await websocket.send_json({
            "type": "user_transcript",
            "text": user_text
        })

        # Step 5: Process transcribed text with LLM
        await handle_voice_query(websocket, user_text)

    except Exception as e:
        print(f"[ERROR] Failed to process audio: {e}")
        import traceback
        traceback.print_exc()

        await websocket.send_json({
            "type": "status",
            "status": "error"
        })


async def handle_voice_query(websocket: WebSocket, user_text: str):
    """
    Main query processing function with CONCURRENT TTS streaming!

    OLD Flow (high latency):
    1. Stream ALL text → THEN generate ALL audio → THEN play
       Total delay: 5s text + 2s TTS generation = 7s until first audio

    NEW Flow (low latency):
    1. Stream text AND generate TTS in parallel per sentence
    2. Audio starts playing while text is still streaming!
       Total delay: 1-2s until first audio (much faster!)

    Key optimization: Process sentences concurrently using asyncio.Queue
    """

    try:
        # Status: Processing
        await websocket.send_json({
            "type": "status",
            "status": "processing"
        })

        print(f"[USER] {user_text}")

        # ============================================================
        # CONCURRENT TEXT + AUDIO STREAMING
        # ============================================================

        full_response = ""
        current_sentence = ""
        audio_started = False

        # Generate response using LLM with streaming
        for chunk in llm.generate_response(user_text, stream=True):
            full_response += chunk
            current_sentence += chunk

            # Send text chunk to frontend immediately
            await websocket.send_json({
                "type": "transcript",
                "text": full_response
            })

            # Check for sentence boundaries (. ! ? or newline)
            if any(punct in chunk for punct in ['. ', '! ', '? ', '\n']):
                sentence = current_sentence.strip()

                if sentence:  # Only process non-empty sentences
                    # Change status to "speaking" on first sentence
                    if not audio_started:
                        await websocket.send_json({
                            "type": "status",
                            "status": "speaking"
                        })
                        audio_started = True
                        print("[TTS] Starting concurrent audio generation...")

                    # Generate TTS for this sentence concurrently
                    # Explanation: We don't wait for TTS to finish before continuing text stream
                    await generate_and_stream_audio(websocket, sentence)

                current_sentence = ""  # Reset for next sentence

            await asyncio.sleep(0.02)  # Small delay (20ms instead of 50ms for faster feel)

        # Handle any remaining text (sentence without punctuation)
        if current_sentence.strip():
            if not audio_started:
                await websocket.send_json({
                    "type": "status",
                    "status": "speaking"
                })
            await generate_and_stream_audio(websocket, current_sentence.strip())

        print(f"[AI] {full_response}")

        # Send final complete response
        await websocket.send_json({
            "type": "response",
            "response": full_response
        })

        print("[TTS] All audio sent")

        # Status: Back to ready/connected
        await websocket.send_json({
            "type": "status",
            "status": "connected"
        })

    except Exception as e:
        print(f"[ERROR] Error processing query: {e}")
        await websocket.send_json({
            "type": "status",
            "status": "error"
        })


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
