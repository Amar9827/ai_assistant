#!/usr/bin/env python
"""Measure TTS latency: cold start vs warm calls."""

import time
from src.core.tts import TextToSpeech
from config.settings import Settings

def measure_three_calls():
    """Measure cold + 2 warm calls from fresh backend start."""
    settings = Settings()
    tts = TextToSpeech(settings)

    print("=== FRESH BACKEND START ===")
    print("Initializing (load ONNX model)...")
    init_start = time.time()
    tts.initialize()
    init_time = time.time() - init_start
    print(f"Initialization time: {init_time:.3f}s")
    print(f"Voice: {settings.PIPER_VOICE}, Speaker: {settings.PIPER_SPEAKER}")
    print()

    test_sentence = "Hello, how are you today?"
    results = []

    for i in range(1, 4):
        print(f"Call #{i} (synthesize): '{test_sentence}'")
        start_time = time.time()
        audio = tts.synthesize(test_sentence)
        latency = time.time() - start_time
        results.append(latency)
        print(f"  Latency: {latency:.3f}s ({len(audio)} samples)")
        print()

    print("="*60)
    print("RESULTS:")
    print(f"  Initialization (ONNX load): {init_time:.3f}s")
    print(f"  Call #1 (cold):   {results[0]:.3f}s")
    print(f"  Call #2 (warm):   {results[1]:.3f}s")
    print(f"  Call #3 (warm):   {results[2]:.3f}s")
    print(f"  Average (warm):   {sum(results[1:])/2:.3f}s")
    print("="*60)

    return init_time, results

if __name__ == "__main__":
    init_time, results = measure_three_calls()
