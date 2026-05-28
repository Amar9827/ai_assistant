#!/usr/bin/env python
"""Measure TTS-per-sentence latency in isolation (subprocess baseline)."""

import time
from src.core.tts import TextToSpeech
from config.settings import Settings

def measure_tts_latency():
    """Measure wall-clock time for single sentence TTS synthesis."""
    settings = Settings()
    tts = TextToSpeech(settings)
    tts.initialize()

    test_sentence = "Hello, how are you today?"
    print(f"Testing TTS with: '{test_sentence}'")
    print(f"Voice: {settings.PIPER_VOICE}, Speaker: {settings.PIPER_SPEAKER}")
    print("Synthesizing...")

    start_time = time.time()
    audio = tts.synthesize(test_sentence)
    end_time = time.time()

    latency = end_time - start_time
    print(f"\n[OK] TTS synthesis complete")
    print(f"Audio samples: {len(audio)}")
    print(f"TTS latency: {latency:.3f} seconds")

    return latency

if __name__ == "__main__":
    latency = measure_tts_latency()
    print(f"\n{'='*50}")
    print(f"BASELINE TTS-PER-SENTENCE: {latency:.3f}s")
    print(f"{'='*50}")
