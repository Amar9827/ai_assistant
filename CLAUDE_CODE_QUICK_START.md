# Claude Code: Quick Start Checklist

Use this to guide your Claude Code sessions step-by-step.

---

## Step 1: Create Frontend (20 mins)

**Paste into Claude Code:**

```
Create a React app with WebSocket connection. Files needed:

1. frontend/package.json
2. frontend/src/App.jsx (main component with WebSocket)
3. frontend/src/App.css (styling)
4. frontend/src/components/StatusBar.jsx
5. frontend/src/components/AudioVisualizer.jsx
6. frontend/src/components/ConversationPanel.jsx
7. frontend/vite.config.js

All code is in CLAUDE_CODE_IMPLEMENTATION.md file. Create exactly as shown there.
```

**Expected outcome:** Frontend connects to `ws://localhost:8000/ws` and shows "Connected"

---

## Step 2: Update Backend to WebSocket (20 mins)

**Paste into Claude Code:**

```
Update backend/server.py to use FastAPI + WebSocket:

1. Replace Flask with FastAPI
2. Add WebSocket endpoint at /ws
3. Stream responses word-by-word (not all at once)
4. For each LLM token: send { type: 'transcript', text: '...' }
5. After full response: send { type: 'response', user_query: '...', response: '...' }

Use the existing Ollama client. Full code in CLAUDE_CODE_IMPLEMENTATION.md
```

**Expected outcome:** Backend streams responses in real-time

---

## Step 3: Add Microphone Input (20 mins)

**Paste into Claude Code:**

```
Add microphone recording to frontend/src/App.jsx:

1. Use navigator.mediaDevices.getUserUserMedia() to access mic
2. Use MediaRecorder API to capture audio
3. When user clicks "Start Listening":
   - Start recording
   - Send audio to backend via WebSocket (as arrayBuffer or blob)
   - Show waveform visualization
4. Show real microphone waveform (50 bars, Web Audio API)

The backend handles transcription - just send raw audio.
```

**Expected outcome:** Waveform shows real microphone input

---

## Step 4: Add Audio Playback (15 mins)

**Paste into Claude Code:**

```
Add audio playback to frontend. When backend sends audio chunks:

1. Receive { type: 'audio_chunk', audio: 'base64_string' }
2. Decode base64 to audio buffer
3. Play immediately (don't wait for all chunks)
4. Use Web Audio API (AudioContext)

This should happen in App.jsx playAudioChunk() function.
```

**Expected outcome:** Response plays as audio while text streams in

---

## Step 5: Add Piper TTS to Backend (20 mins)

**Paste into Claude Code:**

```
Backend needs to stream audio response:

1. After Ollama generates response text
2. Convert to speech using Piper (you have it)
3. Split audio into chunks (~500ms each)
4. Send each chunk via WebSocket as { type: 'audio_chunk', audio: 'base64' }
5. Don't wait for all audio - stream chunks immediately

Update backend/server.py handle_voice_query() function.
```

**Expected outcome:** User hears response played while reading transcript

---

## Step 6: End-to-End Testing (15 mins)

**Paste into Claude Code:**

```
Create a test that verifies the full flow:

1. Frontend connects to backend
2. User types a message or speaks into microphone
3. Backend transcribes (Whisper) and generates response (Ollama)
4. Response text streams word-by-word in real-time
5. Response audio plays while text appears
6. Verify no errors or delays

Create a simple test file or manual steps.
```

**Expected outcome:** Full real-time conversation works

---

## Running Everything

### Terminal 1 (Backend)
```bash
cd backend
python server.py
```

### Terminal 2 (Frontend)
```bash
cd frontend
npm install
npm run dev
```

### Terminal 3 (Browser)
```
Open http://localhost:5173
```

---

## What Each Component Does

| Component | Job |
|-----------|-----|
| **App.jsx** | Manages WebSocket connection + state |
| **StatusBar** | Shows "Connected" / "Listening" / "Processing" / "Speaking" |
| **AudioVisualizer** | Shows microphone waveform + transcript |
| **ConversationPanel** | Chat history display |
| **server.py** | Receives audio → Whisper → Ollama → Piper → sends back |

---

## The Critical Pattern: Streaming

Make sure these work:
- ✅ Response text arrives incrementally (not wait 2s then all at once)
- ✅ Audio chunks play as they arrive (not wait for all)
- ✅ Waveform updates in real-time during listening

If any of these batch/wait instead of stream, the UX feels broken.

---

## Debugging Tips

**"Frontend connects but no response"**
- Check backend logs: `python -u backend/server.py` (unbuffered output)
- Verify Ollama is running: `ollama list`
- Test endpoint: `curl http://localhost:8000/`

**"Response comes all at once, not streaming"**
- Backend needs `async for chunk in ollama.stream():`
- Each chunk must emit immediately, not batch

**"Audio doesn't play"**
- Check browser console for errors
- Verify base64 encoding of audio
- Test audio playback manually in browser console

**"Waveform doesn't move"**
- Check microphone permission granted
- Verify Web Audio API context created
- Check canvas size (should be visible)

---

## What You'll Have After This

✅ Professional-looking UI (like ADA V2)  
✅ Real-time streaming responses (feels alive)  
✅ Microphone input + speaker output  
✅ Ready for v2.0 launch  

---

## Next Steps After This Works

1. Add RAG + personal context (Week 4)
2. Add wake word detection (Week 5)
3. Package as Electron app (Week 6)
4. Deploy / ship (Week 7)

---

## Remember

The difference between a "bot" and a "real AI assistant":
- Bots: Wait for full response, show all at once, feel laggy
- Real: Stream every chunk, update in real-time, feel responsive

You're building the latter. 🚀

---

## File Locations

All starter code is in: `CLAUDE_CODE_IMPLEMENTATION.md`

Copy code directly from there into Claude Code prompts.

---

**Good luck! You've got this.** 💪
