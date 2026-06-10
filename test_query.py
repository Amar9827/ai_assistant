#!/usr/bin/env python
"""Quick test of web-enabled query through backend."""
import asyncio
import websockets
import json
import sys

async def test():
    try:
        async with websockets.connect('ws://localhost:8000/ws') as ws:
            print('[TEST] Connected to backend')
            
            # Send a text query about weather
            await ws.send(json.dumps({'type': 'text_query', 'text': 'What is the weather in London today?'}))
            print('[TEST] Sent query')
            
            # Receive responses
            for i in range(20):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                    data = json.loads(msg)
                    msg_type = data.get('type', 'unknown')
                    status = data.get('status')
                    text = data.get('text')
                    
                    if text and len(text) > 100:
                        text = text[:100] + '...'
                    
                    if status:
                        print(f'[{i:2}] {msg_type:12} status={status}')
                    elif text:
                        print(f'[{i:2}] {msg_type:12} {text}')
                    else:
                        print(f'[{i:2}] {msg_type:12}')
                        
                except asyncio.TimeoutError:
                    print('[END] Stream timeout - response complete')
                    break
    except Exception as e:
        print(f'[ERROR] {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(test())
