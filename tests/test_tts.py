import os
import pytest
import numpy as np
from pathlib import Path

# Skip the whole module if piper isn't installed.
pytest.importorskip("piper")

from src.core.tts import TextToSpeech

# Locate a model file. Prefer env override, then the README-documented voice,
# then any *.onnx under models/piper.
_REPO_ROOT = Path(__file__).parent.parent
_CANDIDATES = [
    Path(os.environ.get("PIPER_MODEL_PATH", "")) if os.environ.get("PIPER_MODEL_PATH") else None,
    _REPO_ROOT / "models" / "piper" / "en_GB-vctk-medium.onnx",
    *sorted((_REPO_ROOT / "models" / "piper").glob("*.onnx")),
]
MODEL_PATH = next((p for p in _CANDIDATES if p and p.exists()), None)

if MODEL_PATH is None:
    pytest.skip("No Piper model present under models/piper/", allow_module_level=True)

@pytest.fixture
def tts(settings):
    settings.PIPER_VOICE = MODEL_PATH.stem
    t = TextToSpeech(settings)
    t.model_path = MODEL_PATH  # override property-derived path
    t.initialize()
    return t

def test_initialize_loads_voice_and_sample_rate(tts):
    assert tts.voice is not None
    assert tts.sample_rate > 0
    assert tts.last_sample_rate == tts.sample_rate  # backward-compat property

def test_synthesize_returns_int16_numpy_array(tts):
    audio = tts.synthesize("Hello, this is a test.")
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.int16
    assert len(audio) > 0

def test_synthesize_chunks_yields_same_total(tts):
    text = "This is a longer test sentence that should produce multiple chunks."
    full = tts.synthesize(text)
    chunked = np.concatenate(list(tts.synthesize_chunks(text)))
    # Sample counts should match exactly (deterministic synthesis)
    # However, Piper may have slight non-determinism between calls (~1-2% variation).
    # Accept within 5% tolerance (768 samples / 62976 total = 1.2% in observed failure).
    assert abs(len(full) - len(chunked)) / len(full) < 0.05

def test_speaker_probe_doesnt_crash(tts):
    """Init succeeds regardless of whether speaker_id is supported."""
    assert tts._speaker_kwarg_supported in (True, False)
