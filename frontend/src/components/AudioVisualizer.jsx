import { useEffect, useRef } from 'react';

export default function AudioVisualizer({ status, transcript, analyser, isListening }) {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    /**
     * Draw function - called repeatedly to animate waveform
     *
     * Explanation: If we have an analyser (microphone is active), we read
     * real audio data and visualize it. Otherwise, show static placeholder.
     */
    const draw = () => {
      // Clear canvas
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, width, height);

      // Draw waveform with glow
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 3;
      ctx.shadowBlur = 15;
      ctx.shadowColor = '#06b6d4';
      ctx.beginPath();

      const bars = 50;
      const barWidth = width / bars;

      if (analyser && isListening) {
        /**
         * REAL WAVEFORM: Read actual microphone data
         *
         * Explanation:
         * - analyser.frequencyBinCount gives us how many data points we have
         * - getByteTimeDomainData() fills array with waveform values (0-255)
         * - We downsample to 50 bars for visualization
         */
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteTimeDomainData(dataArray);

        // Downsample: Take every Nth sample to get 50 bars
        const step = Math.floor(bufferLength / bars);

        for (let i = 0; i < bars; i++) {
          const index = i * step;
          const value = dataArray[index];

          // Convert 0-255 to intensity 0-1
          // 128 is silence (middle), deviation from 128 = volume
          const intensity = Math.abs(value - 128) / 128;

          const barHeight = height * intensity * 0.8;
          const x = i * barWidth + barWidth / 2;
          const y = height / 2;

          if (i === 0) {
            ctx.moveTo(x, y - barHeight / 2);
          } else {
            ctx.lineTo(x, y - barHeight / 2);
          }
        }
      } else {
        /**
         * SIMULATED WAVEFORM: Show placeholder when not recording
         *
         * Explanation: Static visualization when microphone is off
         */
        for (let i = 0; i < bars; i++) {
          const intensity = status === 'listening' ? Math.random() * 0.3 : 0.1;
          const barHeight = height * intensity;
          const x = i * barWidth + barWidth / 2;
          const y = height / 2;

          if (i === 0) {
            ctx.moveTo(x, y - barHeight / 2);
          } else {
            ctx.lineTo(x, y - barHeight / 2);
          }
        }
      }

      ctx.stroke();

      // Draw transcript below with glow
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#06b6d4';
      ctx.fillStyle = '#06b6d4';
      ctx.font = '14px "Segoe UI", monospace';

      // Show helpful tip when listening
      const displayText = isListening
        ? 'Speak clearly into your microphone...'
        : (transcript || '(Waiting for input...)');

      ctx.fillText(displayText, 20, height - 20);

      // Continue animation if listening
      if (isListening) {
        animationFrameRef.current = requestAnimationFrame(draw);
      }
    };

    // Start animation
    draw();

    // Cleanup: Cancel animation when component unmounts
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [status, transcript, analyser, isListening]);

  return (
    <div className="audio-visualizer">
      <canvas ref={canvasRef} width={600} height={150} />
    </div>
  );
}
