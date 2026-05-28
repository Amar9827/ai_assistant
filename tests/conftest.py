import pytest
from pathlib import Path
from config.settings import Settings

@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Settings pointing at a temp dir so tests don't need real models."""
    monkeypatch.setenv("OLLAMA_HOST", "http://test-fake:11434")
    s = Settings()
    # Override paths to tmp
    s.MODELS_DIR = tmp_path / "models"
    s.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    (s.MODELS_DIR / "piper").mkdir(exist_ok=True)
    return s
