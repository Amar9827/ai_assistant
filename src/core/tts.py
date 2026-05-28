"""
In-process Piper TTS using the piper-tts >=1.3.0 Python API.

This module loads PiperVoice once at startup and reuses the ONNX session
for every synthesize() call, eliminating the per-sentence subprocess
overhead of the legacy implementation.
"""
import logging
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from config.settings import Settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_path: Path = settings.PIPER_MODEL_PATH
        self.voice = None
        self.sample_rate: int = 22050  # Overwritten on initialize()
        self._speaker_id: Optional[int] = None
        self._speaker_kwarg_supported: Optional[bool] = None

    @property
    def last_sample_rate(self) -> int:
        """Backward-compat alias for existing callers in assistant.py and server.py.

        The legacy subprocess implementation only knew the sample rate AFTER
        synthesizing (it was read from the output WAV header), hence the name.
        In the new implementation we know it at load time, but we keep this
        property to avoid touching every callsite.
        """
        return self.sample_rate

    def initialize(self):
        """Load the Piper voice model. Called once at startup."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Piper model not found: {self.model_path}\n"
                f"Download it per README and ensure PIPER_VOICE matches the filename."
            )

        try:
            from piper import PiperVoice
        except ImportError as e:
            raise RuntimeError(
                "piper-tts package not importable. Run: pip install -U 'piper-tts>=1.3.0,<2.0'"
            ) from e

        logger.info("Loading Piper voice: %s", self.model_path)
        self.voice = PiperVoice.load(str(self.model_path))
        self.sample_rate = self.voice.config.sample_rate

        # Detect speaker support. Configured speaker may not be honored if
        # (a) voice is single-speaker, or (b) the installed Piper version
        # doesn't accept speaker_id on synthesize(). We probe once.
        configured_speaker = getattr(self.settings, "PIPER_SPEAKER", 0)
        if configured_speaker and configured_speaker != 0:
            self._probe_speaker_support(configured_speaker)
        else:
            self._speaker_id = None
            self._speaker_kwarg_supported = False

        logger.info(
            "Piper initialized: sample_rate=%d, speaker_id=%s, kwarg_supported=%s",
            self.sample_rate, self._speaker_id, self._speaker_kwarg_supported,
        )

    def _probe_speaker_support(self, speaker_id: int):
        """Try calling synthesize() with speaker_id via SynthesisConfig; fall back if not supported."""
        try:
            from piper.config import SynthesisConfig
            # Drain one chunk to test signature.
            syn_config = SynthesisConfig(speaker_id=speaker_id)
            gen = self.voice.synthesize("test", syn_config=syn_config)
            _ = next(iter(gen), None)
            self._speaker_id = speaker_id
            self._speaker_kwarg_supported = True
            logger.info("Speaker selection via SynthesisConfig(speaker_id=%d) works.", speaker_id)
        except (TypeError, ImportError) as e:
            logger.warning(
                "Installed piper-tts does not support SynthesisConfig speaker selection. "
                "PIPER_SPEAKER=%d will be IGNORED. Voice falls back to speaker 0. (%s)",
                speaker_id, type(e).__name__,
            )
            self._speaker_id = None
            self._speaker_kwarg_supported = False
        except Exception as e:
            logger.warning(
                "Speaker probe failed (%s). Falling back to speaker 0.", e,
            )
            self._speaker_id = None
            self._speaker_kwarg_supported = False

    def _synth_kwargs(self) -> dict:
        if self._speaker_kwarg_supported and self._speaker_id is not None:
            from piper.config import SynthesisConfig
            return {"syn_config": SynthesisConfig(speaker_id=self._speaker_id)}
        return {}

    def synthesize(self, text: str) -> np.ndarray:
        """
        Synthesize text to a complete int16 PCM numpy array.

        Buffers all chunks. Call from a thread (asyncio.to_thread) to keep
        the event loop responsive.
        """
        if self.voice is None:
            raise RuntimeError("TTS not initialized; call initialize() first")
        buf = bytearray()
        for chunk in self.voice.synthesize(text, **self._synth_kwargs()):
            buf.extend(chunk.audio_int16_bytes)
        return np.frombuffer(bytes(buf), dtype=np.int16)

    def synthesize_chunks(self, text: str) -> Iterator[np.ndarray]:
        """
        Yield int16 PCM numpy arrays as Piper produces them.

        Useful for streaming to the WebSocket without buffering the whole
        utterance. Stage 1 callers still use synthesize(); this is for Stage 2.
        """
        if self.voice is None:
            raise RuntimeError("TTS not initialized; call initialize() first")
        for chunk in self.voice.synthesize(text, **self._synth_kwargs()):
            yield np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)

    def synthesize_to_file(self, text: str, output_path: str):
        """Compatibility shim — writes a WAV file using the in-process API."""
        import wave
        if self.voice is None:
            raise RuntimeError("TTS not initialized; call initialize() first")
        with wave.open(output_path, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file, **self._synth_kwargs())
