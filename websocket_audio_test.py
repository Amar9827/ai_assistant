#!/usr/bin/env python
"""Test WebSocket audio delivery and save first chunk."""

import asyncio
import websockets
import json
import base64
import wave
import numpy as np

async def test_audio_delivery():
    """Connect, send query, capture first audio chunk."""
    uri = "ws://localhost:8000/ws"

    print("Connecting to backend...")
    async with websockets.connect(uri) as ws:
        # Wait for connection
        msg = await ws.recv()
        print(f"Connected: {json.loads(msg)}")

        # Send query
        test_query = "Testing voice quality with speaker seventeen."
        print(f"\nSending: '{test_query}'")
        await ws.send(json.dumps({
            "type": "text_query",
            "text": test_query
        }))

        # Wait for first audio chunk
        chunk_count = 0
        sample_rate = None

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
            data = json.loads(msg)

            if data["type"] == "status":
                print(f"Status: {data['status']}")

            elif data["type"] == "audio_chunk":
                chunk_count += 1
                if chunk_count == 1:
                    # Save first chunk
                    audio_b64 = data["audio"]
                    sample_rate = data["sample_rate"]

                    # Decode
                    binary = base64.b64decode(audio_b64)
                    audio_array = np.frombuffer(binary, dtype=np.int16)

                    print(f"\n[OK] First audio chunk received!")
                    print(f"  Samples: {len(audio_array)}")
                    print(f"  Sample rate: {sample_rate}Hz")
                    print(f"  Duration: {len(audio_array)/sample_rate:.3f}s")
                    print(f"  Format: int16 PCM")

                    # Save to file
                    output = "websocket_chunk.wav"
                    with wave.open(output, "wb") as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(audio_array.tobytes())

                    print(f"  Saved to: {output}")

                    # Check for artifacts
                    max_val = np.max(np.abs(audio_array))
                    print(f"  Peak amplitude: {max_val} / 32768 ({max_val/32768*100:.1f}%)")
                    if max_val > 30000:
                        print("  WARNING: Possible clipping detected!")
                    else:
                        print("  [OK] No clipping")

                    return True

            elif data["type"] == "response":
                break

if __name__ == "__main__":
    try:
        asyncio.run(test_audio_delivery())
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
