#!/usr/bin/env python
"""Extended test to check for backend hangs."""
import asyncio
import websockets
import json
import sys
import time

async def test():
    try:
        async with websockets.connect('ws://localhost:8000/ws') as ws:
            print('[TEST] Connected to backend')
            
            # Send weather query (should trigger web-search)
            await ws.send(json.dumps({'type': 'text_query', 'text': 'What is the weather in London today?'}))
            print('[TEST] Sent query, waiting for response...')
            
            start_time = time.time()
            max_wait = 20  # 20 second timeout
            msg_count = 0
            
            while time.time() - start_time < max_wait:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    data = json.loads(msg)
                    msg_type = data.get('type')
                    elapsed = time.time() - start_time
                    
                    if msg_type == 'transcript':
                        text = data.get('text', '')[:50]
                        print(f'[{elapsed:5.1f}s] transcript: {text}...')
                    elif msg_type == 'status':
                        status = data.get('status', '')
                        print(f'[{elapsed:5.1f}s] status: {status}')
                    elif msg_type == 'response':
                        text = data.get('response', '')[:80]
                        print(f'[{elapsed:5.1f}s] response: {text}...')
                    else:
                        print(f'[{elapsed:5.1f}s] {msg_type}')
                        
                except asyncio.TimeoutError:
                    pass  # No message, continue waiting
                    
            if msg_count == 0:
                print(f'[FAILED] No messages received after {max_wait}s')
            else:
                print(f'[OK] Received {msg_count} messages')
                
    except Exception as e:
        print(f'[ERROR] {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
