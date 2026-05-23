import subprocess
import wave
import io
from pathlib import Path
from config.settings import Settings
import numpy as np

class TextToSpeech:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_path = settings.PIPER_MODEL_PATH
        self.last_sample_rate = 22050  # Default for most Piper voices

    def initialize(self):
        """Verify Piper is installed and model exists"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {self.model_path}")

        # Check if piper is available (it's installed as a Python module)
        try:
            import piper
        except ImportError:
            raise RuntimeError("Piper TTS not installed")

    def synthesize(self, text: str) -> np.ndarray:
        """Convert text to speech audio"""
        import sys
        import os
        import tempfile
        import wave

        # Use temp file instead of --output-raw
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Use relative path from project root (this is what works in command line)
            relative_model = f"models/piper/{self.settings.PIPER_VOICE}.onnx"

            # Run Piper TTS to file
            cmd = [
                sys.executable, "-m", "piper",
                "--model", relative_model,
                "--output_file", tmp_path
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.settings.PROJECT_ROOT)  # Run from project root
            )

            _, error = process.communicate(input=text.encode('utf-8'))

            if process.returncode != 0:
                raise RuntimeError(f"Piper TTS failed: {error.decode()}")

            # Read the WAV file and store sample rate
            with wave.open(tmp_path, 'rb') as wf:
                self.last_sample_rate = wf.getframerate()  # Store for playback
                audio_data = wf.readframes(wf.getnframes())
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

            return audio_array

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def synthesize_to_file(self, text: str, output_path: str):
        """Generate speech and save to file"""
        import sys
        subprocess.run(
            [
                sys.executable, "-m", "piper",
                "--model", str(self.model_path),
                "--output_file", output_path
            ],
            input=text.encode('utf-8'),
            check=True
        )
