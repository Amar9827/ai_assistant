export default function InputBar({
  textInput,
  setTextInput,
  onSend,
  onStartListening,
  onStopListening,
  onClear,
  onCancel,
  isListening,
  status,
  disabled,
}) {
  const handleKey = (e) => {
    if (e.key === 'Enter') onSend();
  };

  return (
    <div className="input-bar">
      <div className="input-bar-row">
        {/* Mic button */}
        <button
          className={`input-mic ${isListening ? 'active' : ''}`}
          onClick={isListening ? onStopListening : onStartListening}
          disabled={disabled && !isListening}
          title={isListening ? 'Stop recording' : 'Start recording'}
        >
          🎤
        </button>

        {/* Text input */}
        <input
          type="text"
          className="input-field"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Speak, Sir..."
          disabled={disabled}
        />

        {/* Send button */}
        <button
          className="input-send"
          onClick={onSend}
          disabled={disabled || !textInput.trim()}
          title="Send message"
        >
          ▶
        </button>
      </div>

      {/* Controls row */}
      <div className="input-controls">
        <button
          className="ctrl-btn"
          onClick={onStopListening}
          disabled={!isListening}
        >
          ■ STOP
        </button>
        {(status === 'processing' || status === 'speaking') && (
          <button
            className="ctrl-btn abort-btn"
            onClick={onCancel}
            title="Abort current response"
          >
            ⊗ ABORT
          </button>
        )}
        <button className="ctrl-btn" onClick={onClear}>
          ✕ CLEAR
        </button>
      </div>
    </div>
  );
}
