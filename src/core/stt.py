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
        """
        Convert audio to text with optimized parameters for accuracy

        Parameters explained:
        - beam_size=10: Use 10 beams instead of 5 (more thorough search)
        - best_of=5: Consider top 5 candidates (reduces hallucinations)
        - temperature=0.0: Greedy decoding (most confident predictions)
        - vad_filter=True: Remove silence automatically
        - condition_on_previous_text=False: Prevent repetition loops
        """
        # Convert int16 to float32 if needed
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio_data,
            language="en",
            beam_size=10,
            best_of=5,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    def transcribe_file(self, audio_path: str, initial_prompt: str = None) -> str:
        """
        Transcribe audio file with optimized parameters

        Args:
            audio_path: Path to audio file
            initial_prompt: Optional context hint for Whisper (helps with technical terms)

        Same parameters as transcribe() for consistency
        """

        # Default prompt helps with general voice assistant queries
        if initial_prompt is None:
            initial_prompt = (
                "This is a conversation with an AI voice assistant. "
                "The user is asking questions about various topics including "
                "technology, science, general knowledge, and daily tasks."
            )

        segments, info = self.model.transcribe(
            audio_path,
            language="en",
            beam_size=10,
            best_of=5,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt
        )
        text = " ".join([segment.text for segment in segments])
        return text.strip()
