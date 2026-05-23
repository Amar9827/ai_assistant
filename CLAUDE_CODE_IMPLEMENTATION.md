# AI Assistant v2.0 - Implementation Guide for Claude Code

**Goal:** Add real-time UI + WebSocket streaming to transform your terminal-based assistant into a professional real-time voice app (like ADA V2).

**Timeline:** 3 weeks  
**Starting Point:** Your working `ai_assistant` with Whisper + Ollama + Piper  
**Ending Point:** Desktop app with streaming responses + beautiful UI

---

## Phase 1: Setup Frontend (Week 1)

### What We're Building
A React app that:
- Shows "Listening" / "Processing" / "Speaking" states in real-time
- Displays transcript as it arrives (word-by-word, not all at once)
- Plays audio chunks as they stream in
- Has a beautiful, clean UI (steal from ADA V2)

### Files to Create

#### 1. **`frontend/package.json`**
```json
{
  "name": "ai-assistant-ui",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0"
  }
}
```

#### 2. **`frontend/src/App.jsx`** (Main Component)
```jsx
import { useState, useEffect, useRef } from 'react';
import './App.css';
import AudioVisualizer from './components/AudioVisualizer';
import ConversationPanel from './components/ConversationPanel';
import StatusBar from './components/StatusBar';

export default function App() {
  const [status, setStatus] = useState('disconnected'); // 'listening' | 'processing' | 'speaking' | 'disconnected'
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState([]); // Chat history
  const [isListening, setIsListening] = useState(false);
  const wsRef = useRef(null);

  // Connect to backend on mount
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      setStatus('connected');
      console.log('Connected to backend');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types from backend
        if (data.type === 'status') {
          setStatus(data.status); // 'listening' | 'processing' | 'speaking'
        } else if (data.type === 'transcript') {
          setTranscript(data.text);
        } else if (data.type === 'response') {
          // Final response - add to chat history
          setMessages([
            ...messages,
            { role: 'user', content: data.user_query },
            { role: 'assistant', content: data.response }
          ]);
          setTranscript('');
        } else if (data.type === 'audio_chunk') {
          // Play audio chunk immediately (streaming)
          playAudioChunk(data.audio);
        }
      } catch (e) {
        console.error('Error parsing message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
    };

    ws.onclose = () => {
      setStatus('disconnected');
      console.log('Disconnected from backend');
      // Retry connection after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };

    wsRef.current = ws;
  };

  const playAudioChunk = (audioBase64) => {
    // Decode base64 audio and play immediately
    const binaryString = atob(audioBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioContext.decodeAudioData(bytes.buffer, (audioBuffer) => {
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0);
    });
  };

  const startListening = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setIsListening(true);
      wsRef.current.send(JSON.stringify({ type: 'start_listening' }));
    }
  };

  const stopListening = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setIsListening(false);
      wsRef.current.send(JSON.stringify({ type: 'stop_listening' }));
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 AI Assistant v2.0</h1>
        <StatusBar status={status} />
      </header>

      <main className="app-main">
        <ConversationPanel messages={messages} currentTranscript={transcript} />
        <AudioVisualizer status={status} transcript={transcript} />
      </main>

      <footer className="app-footer">
        <button 
          onClick={startListening}
          disabled={isListening || status !== 'connected'}
          className="btn btn-primary"
        >
          🎤 {isListening ? 'Listening...' : 'Start Listening'}
        </button>
        
        <button 
          onClick={stopListening}
          disabled={!isListening}
          className="btn btn-secondary"
        >
          ⏹️ Stop
        </button>
      </footer>
    </div>
  );
}
```

#### 3. **`frontend/src/components/StatusBar.jsx`**
```jsx
export default function StatusBar({ status }) {
  const statusMessages = {
    'connected': '✅ Connected',
    'listening': '🎤 Listening...',
    'processing': '⚙️ Processing...',
    'speaking': '🔊 Speaking...',
    'disconnected': '❌ Disconnected',
    'error': '⚠️ Error'
  };

  const statusColors = {
    'connected': '#4CAF50',
    'listening': '#2196F3',
    'processing': '#FF9800',
    'speaking': '#8BC34A',
    'disconnected': '#999',
    'error': '#F44336'
  };

  return (
    <div className="status-bar" style={{ color: statusColors[status] }}>
      {statusMessages[status] || status}
    </div>
  );
}
```

#### 4. **`frontend/src/components/AudioVisualizer.jsx`**
```jsx
import { useEffect, useRef } from 'react';

export default function AudioVisualizer({ status, transcript }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(0, 0, width, height);

    // Draw animated waveform
    ctx.strokeStyle = '#2196F3';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const bars = 50;
    const barWidth = width / bars;

    for (let i = 0; i < bars; i++) {
      // Simulate waveform (in production, use real audio data)
      const intensity = status === 'listening' ? Math.random() * 0.8 : 0.2;
      const barHeight = height * intensity;
      const x = i * barWidth + barWidth / 2;
      const y = height / 2;

      if (i === 0) {
        ctx.moveTo(x, y - barHeight / 2);
      } else {
        ctx.lineTo(x, y - barHeight / 2);
      }
    }

    ctx.stroke();

    // Draw transcript below
    ctx.fillStyle = '#333';
    ctx.font = '16px Arial';
    ctx.fillText(transcript || '(Waiting for input...)', 20, height - 20);
  }, [status, transcript]);

  return (
    <div className="audio-visualizer">
      <canvas ref={canvasRef} width={600} height={150} />
    </div>
  );
}
```

#### 5. **`frontend/src/components/ConversationPanel.jsx`**
```jsx
import { useRef, useEffect } from 'react';

export default function ConversationPanel({ messages, currentTranscript }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="conversation-panel">
      {messages.map((msg, i) => (
        <div key={i} className={`message message-${msg.role}`}>
          <span className="role">{msg.role === 'user' ? '👤' : '🤖'}</span>
          <span className="content">{msg.content}</span>
        </div>
      ))}

      {currentTranscript && (
        <div className="message message-processing">
          <span className="role">📝</span>
          <span className="content">{currentTranscript}</span>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
```

#### 6. **`frontend/src/App.css`** (Styling)
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  height: 100vh;
  overflow: hidden;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: white;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  font-size: 28px;
  margin-bottom: 10px;
}

.status-bar {
  font-size: 14px;
  font-weight: 600;
  transition: color 0.3s ease;
}

.app-main {
  flex: 1;
  display: grid;
  grid-template-rows: 1fr auto;
  gap: 20px;
  padding: 20px;
  overflow-y: auto;
}

.conversation-panel {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  background: #fafafa;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
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

.message-user {
  justify-content: flex-end;
}

.message-assistant {
  justify-content: flex-start;
}

.message-processing {
  justify-content: flex-start;
  opacity: 0.7;
}

.message .role {
  font-size: 20px;
}

.message .content {
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 70%;
  word-wrap: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-user .content {
  background: #667eea;
  color: white;
}

.audio-visualizer {
  display: flex;
  justify-content: center;
  align-items: center;
  background: white;
  border-radius: 8px;
  border: 1px solid #ddd;
  padding: 20px;
}

.audio-visualizer canvas {
  max-width: 100%;
}

.app-footer {
  display: flex;
  gap: 10px;
  padding: 20px;
  justify-content: center;
  border-top: 1px solid #ddd;
  background: #f9f9f9;
}

.btn {
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f44336;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #da190b;
}
```

---

## Phase 2: Update Backend (Week 2)

### What We Need to Change

Your current backend is:
```
Whisper → LLM → Piper → Save audio
```

New backend needs to:
```
WebSocket → Whisper → Stream transcript → LLM → Stream response → Piper → Stream audio
```

### Files to Create/Modify

#### 1. **`backend/server.py`** (FastAPI + WebSocket)
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import base64
import numpy as np
from pathlib import Path

# Import your existing code
from src.core.ollama_client import OllamaClient
from src.core.whisper_handler import WhisperHandler
from src.core.piper_handler import PiperHandler

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI models
ollama = OllamaClient(model="qwen:4b")
whisper = WhisperHandler(model_size="base")
piper = PiperHandler()

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            'type': 'status',
            'status': 'connected'
        })

        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'start_listening':
                await handle_voice_query(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

async def handle_voice_query(websocket: WebSocket, data: dict):
    """Main voice query handler - receives audio, processes, streams response"""
    
    try:
        # Signal: now listening
        await websocket.send_json({
            'type': 'status',
            'status': 'listening'
        })

        # Simulate receiving audio (in production, receive from browser)
        # For now, we'll just get text input
        user_input = data.get('text', '')

        # If no text, transcribe audio
        if not user_input:
            await websocket.send_json({
                'type': 'status',
                'status': 'processing'
            })
            # You'd transcribe audio here
            return

        # Send status: processing
        await websocket.send_json({
            'type': 'status',
            'status': 'processing'
        })

        # Stream response from LLM (word by word)
        full_response = ''
        async for chunk in ollama.stream(user_input):
            full_response += chunk
            
            # Send transcript update (streaming)
            await websocket.send_json({
                'type': 'transcript',
                'text': full_response
            })

            await asyncio.sleep(0.05)  # Small delay for realistic streaming

        # Generate audio
        await websocket.send_json({
            'type': 'status',
            'status': 'speaking'
        })

        # Stream audio chunks
        audio_chunks = await piper.generate_streaming(full_response)
        for chunk in audio_chunks:
            audio_base64 = base64.b64encode(chunk).decode()
            await websocket.send_json({
                'type': 'audio_chunk',
                'audio': audio_base64
            })

        # Send final response
        await websocket.send_json({
            'type': 'response',
            'user_query': user_input,
            'response': full_response
        })

        # Return to listening
        await websocket.send_json({
            'type': 'status',
            'status': 'connected'
        })

    except Exception as e:
        print(f"Error in voice query: {e}")
        await websocket.send_json({
            'type': 'status',
            'status': 'error'
        })

@app.get("/")
async def root():
    return {"status": "running", "websocket": "ws://localhost:8000/ws"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 2. **`backend/streaming_ollama.py`** (Streaming LLM)
```python
import asyncio
from typing import AsyncGenerator
import ollama

class StreamingOllama:
    def __init__(self, model: str = "qwen:4b"):
        self.model = model

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Ollama word by word"""
        
        # Run blocking ollama call in thread pool
        loop = asyncio.get_event_loop()
        
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            stream=True
        )

        for chunk in response:
            text = chunk.get('response', '')
            if text:
                yield text
                await asyncio.sleep(0)  # Yield control to event loop
```

---

## Phase 3: Connect Everything (Week 3)

### 1. Run Backend
```bash
cd backend
python server.py
# Runs on http://localhost:8000
```

### 2. Run Frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### 3. Test Flow
1. Click "Start Listening"
2. Type a message or speak (you'll need to add voice recording)
3. Watch transcript stream in real-time
4. Listen to response play automatically

---

## What to Ask Claude Code

Use this exact prompt to feed to Claude Code:

```
I'm building a real-time AI assistant with streaming responses. I have:
- Backend: FastAPI + Ollama (working)
- Frontend: React (started)
- Need: WebSocket streaming for real-time transcript + audio

Here's my implementation guide:

[Paste this entire document]

Please help me:
1. Complete the frontend React components (AudioVisualizer needs real audio data)
2. Modify backend to properly stream responses
3. Add audio recording from browser microphone
4. Test end-to-end with dummy data

Start with the frontend Audio Visualizer - make it show real microphone input as waveform.
```

---

## Testing Checklist

- [ ] Frontend connects to backend (see "Connected" in status)
- [ ] Click "Start Listening" → status changes to "Processing"
- [ ] Type message → response streams word-by-word in real-time
- [ ] Audio plays after response completes
- [ ] UI shows waveform animation while listening
- [ ] Can stop and start multiple times without errors

---

## After This Works

- Add real voice input (MediaRecorder API)
- Add Whisper transcription
- Add RAG + personal context
- Add Electron wrapper for desktop app
- Ship v2.0!

---

## Key Architectural Pattern to Remember

**Streaming, not batching:**
- ❌ Wait for full response → send all at once
- ✅ Send every chunk as it arrives → feels responsive

This single pattern change is what makes it feel like a "real AI assistant" instead of a bot.

---

**Good luck! You've got this.** 🚀
