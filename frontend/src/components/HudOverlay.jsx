import { useEffect, useRef } from 'react';

export default function HudOverlay() {
  const canvasRef = useRef(null);
  const scanLineRef = useRef(0);
  const scanDirRef = useRef(1);
  const animRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      // Grid lines
      ctx.strokeStyle = '#4dc9f6';
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.04;
      for (let x = 0; x < w; x += 20) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += 20) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Scan line
      ctx.globalAlpha = 0.12;
      const grad = ctx.createLinearGradient(0, 0, w, 0);
      grad.addColorStop(0, 'transparent');
      grad.addColorStop(0.5, '#4dc9f6');
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fillRect(0, scanLineRef.current, w, 1);

      scanLineRef.current += scanDirRef.current * 0.8;
      if (scanLineRef.current >= h) scanDirRef.current = -1;
      if (scanLineRef.current <= 0) scanDirRef.current = 1;

      // Corner brackets
      ctx.globalAlpha = 0.3;
      ctx.strokeStyle = '#1a5a7a';
      ctx.lineWidth = 1.5;
      const bLen = 20;
      const pad = 6;
      const corners = [
        [pad, pad, 1, 1],
        [w - pad, pad, -1, 1],
        [pad, h - pad, 1, -1],
        [w - pad, h - pad, -1, -1],
      ];
      for (const [cx, cy, dx, dy] of corners) {
        ctx.beginPath();
        ctx.moveTo(cx + bLen * dx, cy);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx, cy + bLen * dy);
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}
