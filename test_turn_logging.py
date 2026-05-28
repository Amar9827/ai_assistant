#!/usr/bin/env python
"""Test turn logging via WebSocket."""

import asyncio
import websockets
import json

async def test_turn_logging():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        await ws.recv()  # Connection message

        await ws.send(json.dumps({"type": "text_query", "text": "Hello test"}))

        statuses = []
        got_audio = False

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(msg)

                if data["type"] == "status":
                    statuses.append(data["status"])
                elif data["type"] == "audio_chunk":
                    got_audio = True
                elif data["type"] == "response":
                    break
            except asyncio.TimeoutError:
                break

        print(f"Statuses: {statuses}")
        print(f"Audio played: {got_audio}")
        print("Check backend logs for turn=<id> prefix")

if __name__ == "__main__":
    asyncio.run(test_turn_logging())
