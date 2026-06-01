"""
Live microphone test for openWakeWord 'hey jarvis' detector.

Usage:
    python -m wake_word.test_detector

Say "Hey Jarvis" into your microphone. Live scores are printed every 80ms.
Press Ctrl+C to stop.
"""
import sys
import time
import logging
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280  # 80ms
THRESHOLD = 0.4
DEBOUNCE_SECONDS = 2.0


def main():
    print("Loading openWakeWord model (hey_jarvis, onnx)...")
    model = Model(wakeword_models=["hey_jarvis_v0.1"], inference_framework="onnx")
    model_key = list(model.models.keys())[0]
    print(f"Model loaded: {model_key}")
    print(f"Threshold: {THRESHOLD}")
    print()
    print("=" * 60)
    print("  Listening... say 'Hey Jarvis'")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    last_detection_time = 0.0
    detection_count = 0
    peak_score = 0.0

    def audio_callback(indata, frames, time_info, status):
        nonlocal last_detection_time, detection_count, peak_score

        if status:
            print(f"  [audio status: {status}]")

        audio = indata[:, 0].astype(np.int16)
        prediction = model.predict(audio)
        score = prediction.get(model_key, 0.0)

        # Track peak score
        if score > peak_score:
            peak_score = score

        # Build score bar (scaled to 0-1 range)
        bar_len = int(score * 50)
        bar = "#" * bar_len + "-" * (50 - bar_len)

        if score >= THRESHOLD:
            now = time.time()
            if now - last_detection_time >= DEBOUNCE_SECONDS:
                last_detection_time = now
                detection_count += 1
                print(f"\r  [{bar}] {score:.4f}  *** DETECTED! (#{detection_count}) ***")
            else:
                print(f"\r  [{bar}] {score:.4f}  (debounced)", end="")
        elif score > 0.01:
            print(f"\r  [{bar}] {score:.4f}  (peak: {peak_score:.4f})", end="")
        else:
            print(f"\r  [{bar}] {score:.4f}", end="")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=CHUNK_SAMPLES,
        callback=audio_callback,
    )

    try:
        with stream:
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print()
        print()
        print(f"Stopped. Total detections: {detection_count}")


if __name__ == "__main__":
    main()
