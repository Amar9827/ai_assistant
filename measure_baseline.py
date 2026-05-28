#!/usr/bin/env python
"""Measure time-to-first-audio for baseline."""

import asyncio
import websockets
import json
import time
import sys

async def measure_latency():
    """Connect to backend, send text query, measure time to first audio chunk."""
    uri = "ws://localhost:8000/ws"

    print("Connecting to backend...")
    async with websockets.connect(uri) as ws:
        # Wait for connection confirmation
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"Connected: {data}")

        # Send text query (simpler than audio for baseline)
        test_query = "What is the capital of France?"
        print(f"\nSending query: '{test_query}'")

        start_time = time.time()
        await ws.send(json.dumps({
            "type": "text_query",
            "text": test_query
        }))

        # Wait for first audio chunk
        first_audio_time = None
        audio_chunks = 0

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(msg)

                if data["type"] == "status":
                    print(f"Status: {data['status']}")
                elif data["type"] == "transcript":
                    print(f"Text: {data['text'][:50]}...")
                elif data["type"] == "audio_chunk":
                    audio_chunks += 1
                    if first_audio_time is None:
                        first_audio_time = time.time()
                        latency = first_audio_time - start_time
                        print(f"\n[OK] First audio chunk received!")
                        print(f"[OK] Time-to-first-audio: {latency:.2f} seconds")
                        return latency
                elif data["type"] == "response":
                    print(f"\nFinal response: {data['response'][:80]}...")
                    if first_audio_time is None:
                        print("WARNING: No audio chunks received!")
                        return None
                    break

            except asyncio.TimeoutError:
                print("ERROR: Timeout waiting for response")
                return None

        print(f"Total audio chunks: {audio_chunks}")
        return first_audio_time - start_time if first_audio_time else None

if __name__ == "__main__":
    try:
        latency = asyncio.run(measure_latency())
        if latency:
            print(f"\n{'='*50}")
            print(f"BASELINE TIME-TO-FIRST-AUDIO: {latency:.2f}s")
            print(f"{'='*50}")
            sys.exit(0)
        else:
            print("\nERROR: Could not measure latency")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
