#!/usr/bin/env python
"""Generate test audio and verify properties."""

import wave
from src.core.tts import TextToSpeech
from config.settings import Settings

settings = Settings()
tts = TextToSpeech(settings)
tts.initialize()

test_text = "Hello, this is speaker seventeen. Testing voice quality and sample rate."

print(f"Generating audio: '{test_text}'")
print(f"Speaker: {tts._speaker_id}")
print(f"Sample rate: {tts.sample_rate}Hz")

# Generate audio
audio = tts.synthesize(test_text)
print(f"Generated {len(audio)} samples")
print(f"Duration: {len(audio)/tts.sample_rate:.2f}s")

# Save to WAV for inspection
output_path = "test_speaker17.wav"
with wave.open(output_path, "wb") as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(tts.sample_rate)
    wav_file.writeframes(audio.tobytes())

print(f"\nAudio saved to: {output_path}")
print("\nWAV file properties:")
with wave.open(output_path, "rb") as wav_file:
    print(f"  Channels: {wav_file.getnchannels()}")
    print(f"  Sample width: {wav_file.getsampwidth()} bytes (16-bit)")
    print(f"  Frame rate: {wav_file.getframerate()}Hz")
    print(f"  Frames: {wav_file.getnframes()}")
    print(f"  Duration: {wav_file.getnframes()/wav_file.getframerate():.2f}s")

print("\n✓ Audio file ready for ear-check")
