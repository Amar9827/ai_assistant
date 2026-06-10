#!/usr/bin/env python
"""Check Bitcoin price from JARVIS vs real web data."""
import asyncio
import websockets
import json
import sys
import time

async def ask_jarvis():
    """Ask JARVIS what Bitcoin price is."""
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        print('[JARVIS] Connected, sending query...')
        await ws.send(json.dumps({'type': 'text_query', 'text': 'Look up the winner of the Indian Premier League 2026 on the web.'}))

        final_response = None
        start = time.time()
        while time.time() - start < 20:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                if data.get('type') == 'response':
                    final_response = data.get('response', '')
            except asyncio.TimeoutError:
                if final_response:
                    break
        return final_response

if __name__ == '__main__':
    result = asyncio.run(ask_jarvis())
    print('\n' + '='*60)
    print('JARVIS says:')
    print(result)
    print('='*60)
