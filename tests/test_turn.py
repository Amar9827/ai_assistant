import asyncio
import pytest
from backend.server import Turn

@pytest.mark.asyncio
async def test_turn_spawns_and_tracks_tasks():
    turn = Turn()
    async def work():
        await asyncio.sleep(0.01)
        return "done"
    task = turn.spawn(work())
    result = await task
    assert result == "done"
    assert task not in turn.tasks  # done_callback removes it

@pytest.mark.asyncio
async def test_turn_cancel_stops_inflight_tasks():
    turn = Turn()
    started = asyncio.Event()
    async def long_work():
        started.set()
        await asyncio.sleep(10)
    task = turn.spawn(long_work())
    await started.wait()
    turn.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert turn.cancelled

@pytest.mark.asyncio
async def test_wait_all_returns_even_on_cancellation():
    turn = Turn()
    async def long_work():
        await asyncio.sleep(10)
    turn.spawn(long_work())
    turn.spawn(long_work())
    turn.cancel()
    await turn.wait_all()  # Should not hang
