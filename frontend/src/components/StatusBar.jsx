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
    'connected': '#22c55e',
    'listening': '#06b6d4',
    'processing': '#eab308',
    'speaking': '#06b6d4',
    'disconnected': '#6b7280',
    'error': '#ef4444'
  };

  return (
    <div className="status-bar" style={{ color: statusColors[status] }}>
      {statusMessages[status] || status}
    </div>
  );
}
