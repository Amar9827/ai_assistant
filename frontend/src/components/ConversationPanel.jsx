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
