from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    MODELS_DIR: Path = PROJECT_ROOT / "models"

    # Whisper settings
    WHISPER_MODEL: str = "small"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "auto"  # auto, cpu, cuda
    WHISPER_COMPUTE_TYPE: str = "int8"  # int8, float16, float32

    # Ollama settings
    OLLAMA_MODEL: str = "llama3.2:3b"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_TEMPERATURE: float = 0.7

    # Piper TTS settings
    PIPER_VOICE: str = "en_GB-vctk-medium"
    PIPER_SPEAKER: int = 17

    @property
    def PIPER_MODEL_PATH(self) -> Path:
        """Dynamically build model path from PIPER_VOICE"""
        return self.MODELS_DIR / "piper" / f"{self.PIPER_VOICE}.onnx"

    # Audio settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    AUDIO_FORMAT: str = "int16"

    class Config:
        env_file = ".env"
        case_sensitive = True
