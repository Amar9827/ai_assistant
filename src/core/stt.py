from faster_whisper import WhisperModel
from pathlib import Path
from typing import Optional
import numpy as np
import logging
import io
import tempfile
from config.settings import Settings

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.STT_PROVIDER.lower()
        self.model = None        # local faster-whisper model
        self.groq_client = None  # Groq cloud client

    def initialize(self):
        """Load local Whisper model and optionally set up Groq client."""
        # Always load local model (used as fallback)
        self.model = WhisperModel(
            self.settings.WHISPER_MODEL,
            device=self.settings.WHISPER_DEVICE,
            compute_type=self.settings.WHISPER_COMPUTE_TYPE
        )

        # Set up Groq client if API key is available
        if self.settings.GROQ_API_KEY:
            try:
                import httpx
                from groq import Groq
                self.groq_client = Groq(
                    api_key=self.settings.GROQ_API_KEY,
                    http_client=httpx.Client(verify=False),
                )
                if self.provider == "groq":
                    logger.info(f"STT provider: Groq ({self.settings.GROQ_STT_MODEL}), fallback: local ({self.settings.WHISPER_MODEL})")
                else:
                    logger.info(f"STT provider: local ({self.settings.WHISPER_MODEL}), Groq available as fallback")
            except Exception as e:
                logger.warning(f"Could not initialize Groq STT client: {e}")
                self.groq_client = None
                if self.provider == "groq":
                    self.provider = "local"
                    logger.warning("Falling back to local STT")
        elif self.provider == "groq":
            logger.warning("GROQ_API_KEY not set, falling back to local STT")
            self.provider = "local"

    # ------------------------------------------------------------------
    # Groq cloud transcription
    # ------------------------------------------------------------------
    def _transcribe_groq(self, audio_path: str) -> str:
        """Transcribe using Groq cloud Whisper API."""
        with open(audio_path, "rb") as f:
            transcription = self.groq_client.audio.transcriptions.create(
                file=(Path(audio_path).name, f),
                model=self.settings.GROQ_STT_MODEL,
                language="en",
                response_format="text",
            )
        result = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        return result

    # ------------------------------------------------------------------
    # Local faster-whisper transcription
    # ------------------------------------------------------------------
    def _transcribe_local(self, audio_data: np.ndarray) -> str:
        """Transcribe using local faster-whisper model."""
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio_data,
            language="en",
            beam_size=5,
            best_of=3,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    def _transcribe_local_file(self, audio_path: str, initial_prompt: str = None) -> str:
        """Transcribe a file using local faster-whisper model."""
        if initial_prompt is None:
            initial_prompt = (
                "This is a conversation with an AI voice assistant. "
                "The user is asking questions about various topics including "
                "technology, science, general knowledge, and daily tasks."
            )

        segments, info = self.model.transcribe(
            audio_path,
            language="en",
            beam_size=5,
            best_of=3,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    # ------------------------------------------------------------------
    # Public API (with automatic fallback)
    # ------------------------------------------------------------------
    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio array. Groq primary → local fallback."""
        if self.provider == "groq" and self.groq_client:
            try:
                # Groq needs a file — write a temp WAV
                import soundfile as sf
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    sf.write(tmp.name, audio_data, self.settings.SAMPLE_RATE)
                    return self._transcribe_groq(tmp.name)
            except Exception as e:
                logger.warning(f"Groq STT failed ({e}), falling back to local")
        return self._transcribe_local(audio_data)

    def transcribe_file(self, audio_path: str, initial_prompt: str = None) -> str:
        """Transcribe audio file. Groq primary → local fallback."""
        if self.provider == "groq" and self.groq_client:
            try:
                return self._transcribe_groq(audio_path)
            except Exception as e:
                logger.warning(f"Groq STT failed ({e}), falling back to local")
        return self._transcribe_local_file(audio_path, initial_prompt)
