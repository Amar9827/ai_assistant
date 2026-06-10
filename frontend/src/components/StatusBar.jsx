export default function StatusBar({ status }) {
  const labels = {
    connected: 'READY — AWAITING COMMAND',
    listening: 'RECORDING — SPEAK NOW',
    processing: 'PROCESSING — ANALYSING INPUT',
    speaking: 'RESPONDING — AUDIO PLAYBACK',
    disconnected: 'OFFLINE — RECONNECTING',
    error: 'ERROR — CONNECTION LOST',
  };

  const dotColor = {
    connected: 'var(--cyan)',
    listening: 'var(--green)',
    processing: 'var(--orange)',
    speaking: 'var(--cyan)',
    disconnected: 'var(--red)',
    error: 'var(--red)',
  };

  const active = status === 'listening' || status === 'processing' || status === 'speaking';

  return (
    <div className="hud-statusbar">
      <span
        className={`hud-statusbar-dot ${active ? 'pulse' : ''}`}
        style={{ background: dotColor[status] || 'var(--cyan-dim)' }}
      />
      <span className="hud-statusbar-text">
        {labels[status] || status?.toUpperCase()}
      </span>
    </div>
  );
}
