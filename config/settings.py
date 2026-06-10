from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    MODELS_DIR: Path = PROJECT_ROOT / "models"

    # STT provider: "local" (faster-whisper) or "groq" (cloud)
    STT_PROVIDER: str = "local"

    # Whisper settings (local fallback)
    WHISPER_MODEL: str = "small"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "auto"  # auto, cpu, cuda
    WHISPER_COMPUTE_TYPE: str = "int8"  # int8, float16, float32

    # Groq STT model (uses same GROQ_API_KEY as LLM)
    GROQ_STT_MODEL: str = "whisper-large-v3-turbo"

    # Ollama settings (local LLM)
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_TEMPERATURE: float = 0.7
    MAX_HISTORY_TURNS: int = 10

    # LLM provider: "ollama" (local) or "groq" (cloud)
    LLM_PROVIDER: str = "ollama"

    # Groq settings (cloud LLM — fast inference)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Tavily Web Search API
    TAVILY_API_KEY: str = ""

    # Piper TTS settings
    PIPER_VOICE: str = "en_GB-alan-medium"
    PIPER_SPEAKER: int = 0
    PIPER_LENGTH_SCALE: float = 0.85  # <1.0 = faster speech (0.85 recommended)

    @property
    def PIPER_MODEL_PATH(self) -> Path:
        """Dynamically build model path from PIPER_VOICE"""
        return self.MODELS_DIR / "piper" / f"{self.PIPER_VOICE}.onnx"

    # Audio settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    AUDIO_FORMAT: str = "int16"

    # Security settings
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_AUDIO_MB: str = "10"

    # Idle auto-shutdown (seconds, 0 = disabled)
    IDLE_TIMEOUT_SECONDS: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )
