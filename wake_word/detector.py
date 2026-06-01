import time
import logging
import threading
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SAMPLES = 1280  # 80ms at 16kHz


class OpenWakeWordDetector:
    """Wake word detector using openWakeWord with 'hey jarvis' pre-trained model."""

    def __init__(self, threshold: float = 0.4, debounce_seconds: float = 2.0):
        self.threshold = threshold
        self.debounce_seconds = debounce_seconds
        self._callback: Optional[Callable] = None
        self._last_detection_time: float = 0
        self._stream: Optional[sd.InputStream] = None
        self._running = False

        logger.info("Loading openWakeWord model (hey_jarvis, onnx)...")
        self._model = Model(
            wakeword_models=["hey_jarvis_v0.1"],
            inference_framework="onnx",
        )
        self._model_key = list(self._model.models.keys())[0]
        logger.info(f"Model loaded: {self._model_key}")

    def set_callback(self, callback: Callable):
        """Register a function to call when wake word is detected.

        The callback receives a dict: {"score": float, "model": str}
        """
        self._callback = callback

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if status:
            logger.warning(f"Audio stream status: {status}")

        audio = indata[:, 0].astype(np.int16)
        prediction = self._model.predict(audio)
        score = prediction.get(self._model_key, 0.0)

        if score >= self.threshold:
            now = time.time()
            if now - self._last_detection_time >= self.debounce_seconds:
                self._last_detection_time = now
                logger.info(f"Wake word detected! score={score:.4f}")
                if self._callback:
                    self._callback({"score": score, "model": self._model_key})

    def start(self):
        """Start listening for wake word (non-blocking)."""
        if self._running:
            logger.warning("Detector already running")
            return

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SAMPLES,
            callback=self._audio_callback,
        )
        self._stream.start()
        self._running = True
        logger.info(f"Listening for '{self._model_key}' (threshold={self.threshold})")

    def stop(self):
        """Stop listening."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        logger.info("Detector stopped")

    @property
    def is_running(self) -> bool:
        return self._running
