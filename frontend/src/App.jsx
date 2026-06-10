import { useState, useEffect, useRef } from 'react';
import './App.css';
import HudOverlay from './components/HudOverlay';
import HudHeader from './components/HudHeader';
import StatusBar from './components/StatusBar';
import ChatPanel from './components/ChatPanel';
import InputBar from './components/InputBar';

export default function App() {
  const [status, setStatus] = useState('disconnected'); // 'listening' | 'processing' | 'speaking' | 'disconnected'
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState([]); // Chat history
  const [isListening, setIsListening] = useState(false);
  const [textInput, setTextInput] = useState(''); // Text input for testing
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const audioChunksRef = useRef([]);
  const playbackContextRef = useRef(null);  // Separate context for playback
  const playbackTimeRef = useRef(0);  // Track playback position for seamless streaming

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

        // DEBUG: Log all incoming messages
        console.log('[WebSocket] Received:', data.type, data);

        // Handle different message types from backend
        if (data.type === 'status') {
          setStatus(data.status); // 'listening' | 'processing' | 'speaking'
        } else if (data.type === 'wake_word_detected') {
          // Wake word "Hey Jarvis" was detected!
          console.log('🎤 Wake word detected:', data.wake_word);
          handleWakeWordDetected();
        } else if (data.type === 'user_transcript') {
          // User's transcribed speech - add to chat immediately
          // Explanation: Show what user said BEFORE assistant responds
          setMessages(prev => [
            ...prev,
            { role: 'user', content: data.text }
          ]);
          setTranscript(''); // Clear any in-progress transcript
        } else if (data.type === 'transcript') {
          // Assistant's streaming response text
          setTranscript(data.text);
        } else if (data.type === 'response') {
          // Final response - add assistant message to history
          // User message was already added via 'user_transcript', so only add assistant
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: data.response }
          ]);
          setTranscript('');
        } else if (data.type === 'audio_chunk') {
          // Play audio chunk immediately (streaming)
          // Pass complete data object (includes sample_rate, dtype)
          playAudioChunk(data);
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

  const playAudioChunk = (data) => {
    /**
     * Play audio chunk with seamless streaming
     *
     * Challenge: We receive raw PCM audio chunks, not complete audio files
     * Solution: Create AudioBuffer from raw PCM and schedule playback
     *
     * Explanation of approach:
     * 1. Decode base64 → raw bytes (int16 PCM audio data)
     * 2. Convert int16 → float32 (Web Audio API format)
     * 3. Create AudioBuffer and fill with samples
     * 4. Schedule playback to continue from previous chunk (seamless)
     */

    try {
      const { audio: audioBase64, sample_rate, dtype } = data;

      // Step 1: Decode base64 to raw bytes
      const binaryString = atob(audioBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Step 2: Convert bytes to Int16Array (PCM audio format from backend)
      const int16Array = new Int16Array(bytes.buffer);
      const numSamples = int16Array.length;

      // Step 3: Initialize playback AudioContext (once)
      if (!playbackContextRef.current) {
        playbackContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        playbackTimeRef.current = playbackContextRef.current.currentTime;
        console.log('[AUDIO] Playback AudioContext initialized');
      }

      const audioContext = playbackContextRef.current;

      // Step 4: Create AudioBuffer
      // Explanation: AudioBuffer = container for audio samples in memory
      const audioBuffer = audioContext.createBuffer(
        1,              // channels (1 = mono)
        numSamples,     // length in samples
        sample_rate     // sample rate (22050 Hz for Piper)
      );

      // Step 5: Convert int16 PCM to float32 (Web Audio format)
      // Explanation: int16 range [-32768, 32767] → float range [-1.0, 1.0]
      const channelData = audioBuffer.getChannelData(0);
      for (let i = 0; i < numSamples; i++) {
        channelData[i] = int16Array[i] / 32768.0;
      }

      // Step 6: Create audio source and schedule playback
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      // Schedule to play immediately after previous chunk
      // Explanation: This creates seamless playback without gaps
      const startTime = Math.max(playbackTimeRef.current, audioContext.currentTime);
      source.start(startTime);

      // Update playback position for next chunk
      playbackTimeRef.current = startTime + audioBuffer.duration;

      console.log(`[AUDIO] Playing chunk: ${numSamples} samples, ${audioBuffer.duration.toFixed(2)}s`);

    } catch (error) {
      console.error('[AUDIO] Error playing audio chunk:', error);
    }
  };

  const handleWakeWordDetected = () => {
    /**
     * Handle wake word detection - auto-start recording
     *
     * Called when backend receives "Hey Jarvis" from wake word service
     * Automatically starts recording without user clicking the button
     */
    console.log('[WAKE WORD] Auto-starting recording...');

    // Visual feedback - flash the screen or show indicator
    // Add a CSS class to trigger animation
    document.body.classList.add('wake-word-active');
    setTimeout(() => {
      document.body.classList.remove('wake-word-active');
    }, 800);

    // Show alert temporarily for obvious feedback
    const alertDiv = document.createElement('div');
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '50%';
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translate(-50%, -50%)';
    alertDiv.style.backgroundColor = '#06b6d4';
    alertDiv.style.color = '#000';
    alertDiv.style.padding = '30px 60px';
    alertDiv.style.fontSize = '32px';
    alertDiv.style.fontWeight = 'bold';
    alertDiv.style.borderRadius = '20px';
    alertDiv.style.boxShadow = '0 0 50px rgba(6, 182, 212, 1)';
    alertDiv.style.zIndex = '9999';
    alertDiv.textContent = '🎤 Wake Word Detected!';
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.remove();
    }, 1000);

    // Auto-start recording if not already listening
    if (!isListening && status === 'connected') {
      startListening();
    }
  };

  const startListening = async () => {
    /**
     * Step 1: Request microphone permission
     *
     * Explanation: Browsers require explicit user permission to access microphone
     * This will show a browser popup asking "Allow microphone access?"
     */
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,      // Mono audio (matches backend expectation)
          sampleRate: 16000,    // 16kHz (Whisper's preferred rate)
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      console.log('[MIC] Microphone access granted');

      /**
       * Step 2: Setup Web Audio API for waveform visualization
       *
       * Explanation: AudioContext lets us analyze audio in real-time
       * AnalyserNode gives us frequency/waveform data for visualization
       */
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 2048; // Controls frequency resolution
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      /**
       * Step 3: Setup MediaRecorder to capture audio
       *
       * Explanation: MediaRecorder captures raw audio data that we'll send to backend
       * We use highest quality settings for better transcription accuracy
       */

      // Try to use high-quality audio format (browser support varies)
      let mimeType = 'audio/webm;codecs=opus';
      let audioBitsPerSecond = 128000; // 128kbps (higher = better quality)

      // Check what formats browser supports
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
        console.log('[MIC] Using WebM Opus format');
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
        console.log('[MIC] Using WebM format');
      } else {
        console.log('[MIC] Using default format');
      }

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: audioBitsPerSecond
      });

      audioChunksRef.current = [];

      // Event: When audio data is available (fires periodically)
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          console.log('[MIC] Audio chunk captured:', event.data.size, 'bytes');
        }
      };

      // Event: When recording stops
      mediaRecorder.onstop = async () => {
        console.log('[MIC] Recording stopped, processing audio...');

        /**
         * Step 4: Combine audio chunks into single blob
         *
         * Explanation: MediaRecorder gives us chunks, we combine them into one file
         */
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log('[MIC] Total audio size:', audioBlob.size, 'bytes');

        /**
         * Step 5: Convert blob to base64 and send to backend
         *
         * Explanation: WebSocket can send text (JSON), so we encode binary audio as base64
         * Backend will decode this back to audio file
         */
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Audio = reader.result.split(',')[1]; // Remove "data:audio/webm;base64," prefix

          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            console.log('[->] Sending audio to backend...');
            wsRef.current.send(JSON.stringify({
              type: 'audio_data',
              audio: base64Audio,
              format: 'webm'
            }));
          }
        };
        reader.readAsDataURL(audioBlob);

        // Cleanup: Stop all audio tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;

      // Start recording!
      mediaRecorder.start();
      setIsListening(true);

      // Notify backend we're listening
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'start_listening' }));
      }

      console.log('[MIC] Recording started');

    } catch (error) {
      console.error('[MIC] Error accessing microphone:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopListening = () => {
    /**
     * Stop recording and process captured audio
     *
     * Explanation: This triggers mediaRecorder.onstop event,
     * which will send the audio to backend for transcription
     */
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      console.log('[MIC] Stopping recording...');
    }

    setIsListening(false);

    // Notify backend
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_listening' }));
    }
  };

  const sendTextQuery = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && textInput.trim()) {
      // Add user message to chat immediately (don't wait for backend)
      // Explanation: Show user's message right away for instant feedback
      setMessages(prev => [
        ...prev,
        { role: 'user', content: textInput }
      ]);

      // Send to backend
      wsRef.current.send(JSON.stringify({
        type: 'text_query',
        text: textInput
      }));

      setTextInput(''); // Clear input
    }
  };

  const handleCancel = () => {
    /**
     * Abort current response - cancel TTS and LLM processing
     * Sends cancel_turn message to backend to stop all in-flight tasks
     */
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel_turn' }));
      console.log('[ABORT] Cancelling current turn...');
    }
  };

  return (
    <div className="app">
      <HudOverlay />
      <HudHeader status={status} />
      <StatusBar status={status} />
      <ChatPanel
        messages={messages}
        currentTranscript={transcript}
        status={status}
        analyser={analyserRef.current}
        isListening={isListening}
      />
      <InputBar
        textInput={textInput}
        setTextInput={setTextInput}
        onSend={sendTextQuery}
        onStartListening={startListening}
        onStopListening={stopListening}
        onCancel={handleCancel}
        onClear={() => { setMessages([]); setTranscript(''); }}
        isListening={isListening}
        status={status}
        disabled={status !== 'connected' && status !== 'listening' && status !== 'processing' && status !== 'speaking'}
      />
    </div>
  );
}
