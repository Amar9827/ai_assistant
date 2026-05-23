from faster_whisper import WhisperModel
from pathlib import Path
from typing import Optional
import numpy as np
from config.settings import Settings

class SpeechToText:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None

    def initialize(self):
        """Load Whisper model"""
        self.model = WhisperModel(
            self.settings.WHISPER_MODEL,
            device=self.settings.WHISPER_DEVICE,
            compute_type=self.settings.WHISPER_COMPUTE_TYPE
        )

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Convert audio to text"""
        # Convert int16 to float32 if needed
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio_data,
            language="en",
            beam_size=5
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe audio file"""
        segments, info = self.model.transcribe(audio_path, language="en")
        text = " ".join([segment.text for segment in segments])
        return text.strip()
