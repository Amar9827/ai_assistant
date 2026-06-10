import { useRef, useEffect } from 'react';

export default function ChatPanel({ messages, currentTranscript, status, analyser, isListening }) {
  const endRef = useRef(null);
  const waveRef = useRef(null);
  const animRef = useRef(null);
  const phaseRef = useRef(0);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentTranscript]);

  // Waveform visualizer
  useEffect(() => {
    const canvas = waveRef.current;
    if (!canvas) return;

    const draw = () => {
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const mid = h / 2;
      ctx.clearRect(0, 0, w, h);

      const phase = phaseRef.current;
      phaseRef.current += 0.06;

      // Determine amplitude and color based on state
      let amp = 0.3;
      let color = '#4dc9f6';
      let level = 0.05;

      if (isListening) {
        color = '#4dc9f6';
        amp = 0.5;
      }
      if (status === 'speaking') {
        color = '#f0a030';
        amp = 0.5;
      }

      // Read real audio level if available
      if (analyser && isListening) {
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          sum += Math.abs(data[i] - 128);
        }
        level = Math.max(sum / data.length / 128 * 4, 0.05);
      } else {
        level = (status === 'speaking') ? 0.4 + 0.2 * Math.sin(phase * 0.7) : 0.05;
      }

      // Primary wave
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      for (let x = 0; x < w; x += 2) {
        const t = (x / w) * 4 * Math.PI;
        const y = mid + Math.sin(t + phase) * mid * amp * level
                      + Math.sin(t * 2.5 - phase * 1.3) * mid * amp * level * 0.4;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Ghost wave
      ctx.globalAlpha = 0.25;
      ctx.beginPath();
      for (let x = 0; x < w; x += 2) {
        const t = (x / w) * 4 * Math.PI;
        const y = mid + Math.sin(t + phase + 1) * mid * amp * level * 0.7;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [status, analyser, isListening]);

  const showWave = isListening || status === 'speaking';

  return (
    <div className="chat-panel">
      {/* Waveform */}
      {showWave && (
        <canvas
          ref={waveRef}
          width={600}
          height={32}
          className="chat-waveform"
        />
      )}

      {/* Processing bar */}
      {status === 'processing' && (
        <div className="chat-processing-bar">
          <div className="chat-processing-fill" />
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !currentTranscript && (
          <div className="chat-empty">
            <div className="chat-empty-greeting">At your service, sir.</div>
            <div className="chat-empty-hint">How may I assist you today?</div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <div className="chat-msg-header">
              <span className={`chat-msg-bar ${msg.role}`} />
              <span className="chat-msg-role">
                {msg.role === 'user' ? 'YOU' : 'JARVIS'}
              </span>
            </div>
            <div className="chat-msg-body">
              <span className={`chat-msg-accent ${msg.role}`} />
              <span className="chat-msg-text">{msg.content}</span>
            </div>
          </div>
        ))}

        {currentTranscript && (
          <div className="chat-msg chat-msg-assistant streaming">
            <div className="chat-msg-header">
              <span className="chat-msg-bar assistant" />
              <span className="chat-msg-role">JARVIS</span>
            </div>
            <div className="chat-msg-body">
              <span className="chat-msg-accent assistant" />
              <span className="chat-msg-text">{currentTranscript}</span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
