# UI Redesign Plan - ADA-Inspired Interface

## Current State Analysis

### What We Have Now
1. **CLI** - Terminal-based, works well
2. **Web UI** - Basic FastAPI + vanilla HTML/JS, minimal features
3. **Gradio GUI** - Auto-generated UI, limited customization, compatibility issues

### Problems with Current UI
- ❌ Gradio has version compatibility issues (format changes)
- ❌ No real-time visual feedback during processing
- ❌ No waveform visualization
- ❌ Separate text/voice tabs feel disconnected
- ❌ No status indicators (listening/processing/speaking)
- ❌ Basic styling, not modern
- ❌ No persistent conversation view across modes

## ADA's UI Architecture

Based on the ADA V2 repository analysis:

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React/Vue)              │
│  - Modern component-based UI                         │
│  - Real-time audio visualization                     │
│  - WebSocket for live updates                        │
│  - Persistent conversation view                      │
└─────────────────┬───────────────────────────────────┘
                  │ Socket.IO / WebSocket
┌─────────────────▼───────────────────────────────────┐
│              Backend (FastAPI)                       │
│  - REST API endpoints                                │
│  - WebSocket handler                                 │
│  - Event-driven architecture                         │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│         Voice Assistant Core (Existing)              │
│  - Whisper, Ollama, Piper (keep as-is)             │
└─────────────────────────────────────────────────────┘
```

## New UI Design

### Technology Stack

**Backend:**
- FastAPI (existing, keep)
- Socket.IO for real-time communication
- Python asyncio for streaming

**Frontend:**
- **Option 1**: Pure HTML/CSS/JavaScript (no build step)
- **Option 2**: React (requires npm/build)
- **Option 3**: Vue.js (lighter than React)

**Recommendation**: **Option 1** (Pure HTML/CSS/JS) for simplicity and no dependencies

### UI Layout

```
┌──────────────────────────────────────────────────────┐
│  🎤 Local AI Voice Assistant                  [⚙️][❌] │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │        Conversation History                    │ │
│  │                                                │ │
│  │  👤 You: What is Python?                      │ │
│  │  🤖 Assistant: Python is a programming...     │ │
│  │                                                │ │
│  │  👤 You: [Recording...]  ████████░░░░         │ │
│  │                                                │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  [Type or click to record...]           [Send] │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  [🎙️ Hold to Talk]  Status: ● Ready               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Key Features

1. **Unified Interface** - No separate tabs, single conversation view
2. **Real-time Status** - Visual indicator (Ready/Listening/Processing/Speaking)
3. **Audio Waveform** - Live visualization during recording
4. **Push-to-Talk** - Hold button to record, release to send
5. **Streaming Response** - Text appears word-by-word as LLM generates
6. **Voice Playback** - Audio plays automatically for voice queries
7. **Conversation Persistence** - All messages in one scrollable view
8. **Modern Design** - Dark mode, smooth animations, responsive

## Implementation Plan

### Phase 1: Backend API Redesign (1 day)

#### 1.1 Add Socket.IO Support

**File**: `src/interfaces/realtime_api.py` (NEW)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import socketio
from src.core.assistant import VoiceAssistant
import asyncio

# Create Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app)

assistant = VoiceAssistant()

@app.on_event("startup")
async def startup():
    assistant.initialize()

# Socket.IO Events
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('status', {'state': 'ready'}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def text_query(sid, data):
    """Handle text query"""
    query = data.get('text', '')
    
    # Update status
    await sio.emit('status', {'state': 'processing'}, room=sid)
    
    # Stream LLM response
    for sentence in assistant.llm.generate_streaming_sentences(query):
        await sio.emit('response_chunk', {'text': sentence}, room=sid)
        await asyncio.sleep(0)  # Yield control
    
    await sio.emit('status', {'state': 'ready'}, room=sid)

@sio.event
async def voice_query(sid, data):
    """Handle voice query with streaming"""
    audio_data = data.get('audio')  # Base64 encoded
    
    await sio.emit('status', {'state': 'transcribing'}, room=sid)
    
    # Decode and transcribe
    import base64
    import numpy as np
    audio_bytes = base64.b64decode(audio_data)
    audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
    
    text = assistant.stt.transcribe(audio_array)
    await sio.emit('transcription', {'text': text}, room=sid)
    
    # Generate response
    await sio.emit('status', {'state': 'generating'}, room=sid)
    
    full_response = ""
    for sentence in assistant.llm.generate_streaming_sentences(text):
        await sio.emit('response_chunk', {'text': sentence}, room=sid)
        full_response += sentence
        await asyncio.sleep(0)
    
    # Generate TTS
    await sio.emit('status', {'state': 'synthesizing'}, room=sid)
    audio = assistant.tts.synthesize(full_response)
    
    # Send audio back
    audio_base64 = base64.b64encode(audio.tobytes()).decode()
    await sio.emit('audio_response', {
        'audio': audio_base64,
        'sample_rate': assistant.tts.last_sample_rate
    }, room=sid)
    
    await sio.emit('status', {'state': 'ready'}, room=sid)

# Serve static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

#### 1.2 Update Requirements

```txt
# Add to requirements.txt
python-socketio>=5.11.0
```

### Phase 2: Frontend Development (2 days)

#### 2.1 HTML Structure

**File**: `static/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local AI Voice Assistant</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎤 Local AI Voice Assistant</h1>
            <div class="status-bar">
                <span class="status-indicator" id="status">● Ready</span>
                <button class="settings-btn" onclick="toggleSettings()">⚙️</button>
            </div>
        </header>

        <div class="conversation" id="conversation">
            <!-- Messages appear here -->
        </div>

        <div class="input-area">
            <textarea 
                id="textInput" 
                placeholder="Type a message or hold the button to speak..."
                rows="1"
            ></textarea>
            <button class="send-btn" onclick="sendText()">Send</button>
            <button 
                class="voice-btn" 
                onmousedown="startRecording()" 
                onmouseup="stopRecording()"
                ontouchstart="startRecording()"
                ontouchend="stopRecording()"
            >
                🎙️ Hold to Talk
            </button>
        </div>

        <canvas id="waveform"></canvas>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

#### 2.2 CSS Styling

**File**: `static/style.css`

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
    color: #e0e0e0;
    height: 100vh;
    overflow: hidden;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 20px;
}

header {
    background: rgba(255, 255, 255, 0.05);
    padding: 15px 20px;
    border-radius: 10px 10px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

h1 {
    font-size: 1.5rem;
    font-weight: 600;
}

.status-bar {
    display: flex;
    align-items: center;
    gap: 15px;
}

.status-indicator {
    font-size: 0.9rem;
    padding: 5px 15px;
    background: rgba(76, 175, 80, 0.2);
    border-radius: 20px;
    color: #4caf50;
}

.status-indicator.processing {
    background: rgba(255, 152, 0, 0.2);
    color: #ff9800;
}

.status-indicator.speaking {
    background: rgba(33, 150, 243, 0.2);
    color: #2196f3;
}

.conversation {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
}

.message {
    margin-bottom: 15px;
    display: flex;
    gap: 10px;
    animation: slideIn 0.3s ease;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.message.user {
    justify-content: flex-end;
}

.message-content {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 18px;
    line-height: 1.5;
}

.message.user .message-content {
    background: #5e5ce6;
    color: white;
}

.message.assistant .message-content {
    background: rgba(255, 255, 255, 0.1);
    color: #e0e0e0;
}

.input-area {
    display: flex;
    gap: 10px;
    padding: 15px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0 0 10px 10px;
}

textarea {
    flex: 1;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 10px;
    color: #e0e0e0;
    font-size: 1rem;
    resize: none;
    font-family: inherit;
}

textarea:focus {
    outline: none;
    border-color: #5e5ce6;
}

button {
    background: #5e5ce6;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: white;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.2s;
}

button:hover {
    background: #4e4cd6;
    transform: translateY(-1px);
}

button:active {
    transform: translateY(0);
}

.voice-btn {
    background: #4caf50;
}

.voice-btn:hover {
    background: #45a049;
}

.voice-btn.recording {
    background: #f44336;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

#waveform {
    position: fixed;
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%);
    display: none;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 10px;
}

#waveform.active {
    display: block;
}

/* Scrollbar styling */
.conversation::-webkit-scrollbar {
    width: 8px;
}

.conversation::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
}

.conversation::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
}

.conversation::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
}
```

#### 2.3 JavaScript Logic

**File**: `static/app.js`

```javascript
// Socket.IO connection
const socket = io();

// DOM elements
const conversation = document.getElementById('conversation');
const textInput = document.getElementById('textInput');
const statusIndicator = document.getElementById('status');
const waveformCanvas = document.getElementById('waveform');
const voiceBtn = document.querySelector('.voice-btn');

// Audio recording
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Connect to server
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('status', (data) => {
    updateStatus(data.state);
});

socket.on('transcription', (data) => {
    addMessage('user', data.text);
});

socket.on('response_chunk', (data) => {
    appendToLastAssistantMessage(data.text);
});

socket.on('audio_response', async (data) => {
    // Play audio response
    const audioData = base64ToArrayBuffer(data.audio);
    playAudio(audioData, data.sample_rate);
});

// Send text message
function sendText() {
    const text = textInput.value.trim();
    if (!text) return;

    addMessage('user', text);
    socket.emit('text_query', { text });
    textInput.value = '';
}

// Enter key to send
textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendText();
    }
});

// Voice recording
async function startRecording() {
    if (isRecording) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const arrayBuffer = await audioBlob.arrayBuffer();
            const float32Array = await audioBufferToFloat32(arrayBuffer);
            
            // Send to server
            const base64Audio = arrayBufferToBase64(float32Array.buffer);
            socket.emit('voice_query', { audio: base64Audio });
        };

        mediaRecorder.start();
        isRecording = true;
        voiceBtn.classList.add('recording');
        voiceBtn.textContent = '🔴 Recording...';
        waveformCanvas.classList.add('active');

        // Visualize audio
        visualizeAudio(stream);
    } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Could not access microphone');
    }
}

function stopRecording() {
    if (!isRecording) return;

    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    isRecording = false;
    voiceBtn.classList.remove('recording');
    voiceBtn.textContent = '🎙️ Hold to Talk';
    waveformCanvas.classList.remove('active');
}

// Add message to conversation
function addMessage(role, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    conversation.appendChild(messageDiv);
    conversation.scrollTop = conversation.scrollHeight;
}

// Append to last assistant message (for streaming)
function appendToLastAssistantMessage(text) {
    const messages = conversation.querySelectorAll('.message.assistant');
    let lastMessage = messages[messages.length - 1];

    if (!lastMessage) {
        // Create new message
        lastMessage = document.createElement('div');
        lastMessage.className = 'message assistant';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        lastMessage.appendChild(contentDiv);
        conversation.appendChild(lastMessage);
    }

    const contentDiv = lastMessage.querySelector('.message-content');
    contentDiv.textContent += text;
    conversation.scrollTop = conversation.scrollHeight;
}

// Update status indicator
function updateStatus(state) {
    const statusMap = {
        'ready': '● Ready',
        'listening': '🎤 Listening',
        'transcribing': '✍️ Transcribing',
        'generating': '🤔 Thinking',
        'synthesizing': '🔊 Speaking',
        'processing': '⚙️ Processing'
    };

    statusIndicator.textContent = statusMap[state] || state;
    statusIndicator.className = `status-indicator ${state}`;
}

// Utility functions
function base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

async function audioBufferToFloat32(arrayBuffer) {
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    return audioBuffer.getChannelData(0);
}

function playAudio(arrayBuffer, sampleRate) {
    const audioContext = new AudioContext({ sampleRate });
    const audioBuffer = audioContext.createBuffer(1, arrayBuffer.byteLength / 2, sampleRate);
    const channelData = audioBuffer.getChannelData(0);
    
    const int16Array = new Int16Array(arrayBuffer);
    for (let i = 0; i < int16Array.length; i++) {
        channelData[i] = int16Array[i] / 32768.0;
    }
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
}

function visualizeAudio(stream) {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    const canvas = waveformCanvas;
    const canvasCtx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    canvas.width = 400;
    canvas.height = 100;

    function draw() {
        if (!isRecording) return;

        requestAnimationFrame(draw);
        analyser.getByteTimeDomainData(dataArray);

        canvasCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

        canvasCtx.lineWidth = 2;
        canvasCtx.strokeStyle = '#4caf50';
        canvasCtx.beginPath();

        const sliceWidth = canvas.width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * canvas.height / 2;

            if (i === 0) {
                canvasCtx.moveTo(x, y);
            } else {
                canvasCtx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        canvasCtx.lineTo(canvas.width, canvas.height / 2);
        canvasCtx.stroke();
    }

    draw();
}
```

### Phase 3: Integration (0.5 days)

#### 3.1 Update Entry Point

**File**: `setup.py`

```python
entry_points={
    "console_scripts": [
        "assistant-cli=src.interfaces.cli:main",
        "assistant-web=src.interfaces.realtime_api:main",  # Updated
        "assistant-gui=src.interfaces.gui:main",  # Keep for fallback
    ],
}
```

#### 3.2 Add Main Function

**File**: `src/interfaces/realtime_api.py`

```python
def main():
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
```

### Phase 4: Testing & Polish (0.5 days)

#### Test Cases
1. ✅ Text message sends and streams response
2. ✅ Voice recording works (hold button)
3. ✅ Transcription appears in chat
4. ✅ Response streams word-by-word
5. ✅ TTS audio plays automatically
6. ✅ Status indicator updates correctly
7. ✅ Waveform visualizes during recording
8. ✅ Mobile responsive (touch events)

## Migration Strategy

### Option A: Replace Immediately
- Delete `gui.py`
- Replace `web.py` with `realtime_api.py`
- Single web interface

### Option B: Keep Both (Recommended)
- Add `realtime_api.py` as new interface
- Keep existing for backup
- Entry points:
  - `assistant-web` → New real-time UI
  - `assistant-gui` → Old Gradio (fallback)

## File Structure After Implementation

```
ai-assistant/
├── src/
│   └── interfaces/
│       ├── cli.py              # Keep
│       ├── realtime_api.py     # NEW (main web interface)
│       ├── gui.py              # Keep as fallback
│       └── web.py              # Deprecated (optional)
├── static/                     # NEW
│   ├── index.html
│   ├── style.css
│   └── app.js
└── requirements.txt            # Add python-socketio
```

## Timeline

| Phase | Duration | Priority |
|-------|----------|----------|
| Backend API (Socket.IO) | 1 day | Critical |
| Frontend HTML/CSS | 1 day | Critical |
| JavaScript Logic | 1 day | Critical |
| Integration & Testing | 0.5 days | High |
| **Total** | **3.5 days** | |

## Benefits Over Current UI

| Feature | Current (Gradio) | New (ADA-Style) |
|---------|------------------|-----------------|
| **Real-time Streaming** | No | Yes ✅ |
| **Unified View** | Separate tabs | Single conversation ✅ |
| **Audio Visualization** | No | Waveform ✅ |
| **Status Indicators** | No | Yes ✅ |
| **Push-to-Talk** | No | Yes ✅ |
| **Modern Design** | Auto-generated | Custom ✅ |
| **Mobile Support** | Limited | Touch events ✅ |
| **Version Issues** | Gradio 6.0 breaks | None ✅ |

## Next Steps

1. ✅ Approve this plan
2. Install Socket.IO: `pip install python-socketio`
3. Create `static/` directory
4. Implement backend (realtime_api.py)
5. Create frontend files (HTML/CSS/JS)
6. Test and iterate

---

**Ready to start implementation?**
