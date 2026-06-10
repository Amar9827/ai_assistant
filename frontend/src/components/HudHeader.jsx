import { useEffect, useRef, useState } from 'react';

export default function HudHeader({ status }) {
  const canvasRef = useRef(null);
  const phaseRef = useRef(0);
  const animRef = useRef(null);
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');

  // Clock
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setDate(now.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase());
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Arc reactor animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const size = 42;
    canvas.width = size;
    canvas.height = size;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);
      const cx = size / 2;
      const cy = size / 2;
      const phase = phaseRef.current;

      // Outer ring segments (4 arcs rotating clockwise)
      for (let i = 0; i < 4; i++) {
        const a = phase + (i * Math.PI) / 2;
        ctx.beginPath();
        ctx.arc(cx, cy, 18, a, a + 1.0);
        ctx.strokeStyle = `rgba(77, 201, 246, ${0.6 + 0.2 * Math.sin(phase + i)})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Middle ring (3 arcs counter-rotating)
      for (let j = 0; j < 3; j++) {
        const b = -phase * 1.4 + (j * 2 * Math.PI) / 3;
        ctx.beginPath();
        ctx.arc(cx, cy, 12, b, b + 0.8);
        ctx.strokeStyle = 'rgba(77, 201, 246, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Inner ring (6 arcs fast rotation)
      for (let k = 0; k < 6; k++) {
        const c = phase * 2 + (k * Math.PI) / 3;
        ctx.beginPath();
        ctx.arc(cx, cy, 7, c, c + 0.4);
        ctx.strokeStyle = 'rgba(77, 201, 246, 0.5)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Core glow
      const connected = status !== 'disconnected' && status !== 'error';
      const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, 5);
      if (connected) {
        grd.addColorStop(0, 'rgba(122, 234, 255, 0.95)');
        grd.addColorStop(1, 'rgba(26, 90, 122, 0)');
      } else {
        grd.addColorStop(0, 'rgba(255, 68, 68, 0.9)');
        grd.addColorStop(1, 'rgba(122, 26, 26, 0)');
      }
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, 2 * Math.PI);
      ctx.fillStyle = grd;
      ctx.fill();

      phaseRef.current += 0.04;
      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [status]);

  const connected = status !== 'disconnected' && status !== 'error';

  return (
    <div className="hud-header">
      <canvas ref={canvasRef} className="hud-reactor" />

      <div className="hud-title-group">
        <div className="hud-title">J.A.R.V.I.S.</div>
        <div className="hud-subtitle">JUST A RATHER VERY INTELLIGENT SYSTEM</div>
      </div>

      <div className="hud-header-right">
        <div className="hud-clock">
          <div className="hud-time">{time}</div>
          <div className="hud-date">{date}</div>
        </div>
        <div className={`hud-status-dot ${connected ? 'connected' : 'disconnected'}`} />
      </div>
    </div>
  );
}
