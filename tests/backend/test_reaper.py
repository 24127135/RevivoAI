"""
Tests for backend/reaper.py

Naming follows README.md conventions:
    test_<component>_<scenario>_<expected_behavior>
Run with: poetry run pytest tests/backend/test_reaper.py -v
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.reaper import session_reaper_task


# ---------------------------------------------------------------------------
# Cancellation semantics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reaper_cancel_during_reap_call_propagates_and_marks_task_cancelled():
    handler = AsyncMock()

    async def slow_reap():
        await asyncio.sleep(1.0)
        return 0

    handler.reap_expired_sessions.side_effect = slow_reap

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=300))
    await asyncio.sleep(0.05)  # ensure we're inside the reap() await
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled() is True


@pytest.mark.asyncio
async def test_reaper_cancel_during_normal_sleep_propagates_and_marks_task_cancelled():
    handler = AsyncMock()
    handler.reap_expired_sessions.return_value = 0

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=300))
    await asyncio.sleep(0.05)  # reap() already returned; now inside sleep(300)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled() is True


@pytest.mark.asyncio
async def test_reaper_cancel_during_error_backoff_sleep_propagates_and_marks_task_cancelled():
    handler = AsyncMock()
    handler.reap_expired_sessions.side_effect = RuntimeError("db down")

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=10))
    await asyncio.sleep(0.05)  # error already raised; now inside the backoff sleep
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled() is True


# ---------------------------------------------------------------------------
# Loop behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reaper_calls_reap_expired_sessions_repeatedly(monkeypatch):
    handler = AsyncMock()
    handler.reap_expired_sessions.return_value = 0
    # Neutralize the 0-5s random jitter so cycle timing is deterministic here.
    monkeypatch.setattr("backend.reaper.random.uniform", lambda a, b: 0)

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=0.02))
    await asyncio.sleep(0.15)  # allow several real cycles to elapse
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert handler.reap_expired_sessions.call_count >= 2


@pytest.mark.asyncio
async def test_reaper_survives_transient_exception_and_keeps_looping(monkeypatch):
    handler = AsyncMock()
    handler.reap_expired_sessions.side_effect = [RuntimeError("db down"), 0, 0, 0, 0]
    monkeypatch.setattr("backend.reaper.random.uniform", lambda a, b: 0)

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=0.02))
    await asyncio.sleep(0.15)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # One bad cycle must not kill the loop.
    assert handler.reap_expired_sessions.call_count >= 2


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reaper_backoff_doubles_on_consecutive_failures(monkeypatch):
    handler = AsyncMock()
    handler.reap_expired_sessions.side_effect = RuntimeError("db down")

    sleep_calls = []

    async def spy_sleep(seconds, *a, **kw):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 3:
            raise asyncio.CancelledError()

    monkeypatch.setattr("backend.reaper.asyncio.sleep", spy_sleep)

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=10))
    with pytest.raises(asyncio.CancelledError):
        await task

    # base=10 -> 10*2^0=10, 10*2^1=20, 10*2^2=40 ...
    assert sleep_calls[0] == 10
    assert sleep_calls[1] == 20
    assert sleep_calls[2] == 40


@pytest.mark.asyncio
async def test_reaper_backoff_is_capped_at_max_backoff(monkeypatch):
    handler = AsyncMock()
    handler.reap_expired_sessions.side_effect = RuntimeError("db down")

    sleep_calls = []

    async def spy_sleep(seconds, *a, **kw):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 8:
            raise asyncio.CancelledError()

    monkeypatch.setattr("backend.reaper.asyncio.sleep", spy_sleep)

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=1000))
    with pytest.raises(asyncio.CancelledError):
        await task

    # 1000 * 2^n grows past 3600 quickly; every call must be capped there.
    assert max(sleep_calls) <= 3600
    assert sleep_calls[-1] == 3600


@pytest.mark.asyncio
async def test_reaper_consecutive_error_count_resets_after_success(monkeypatch):
    handler = AsyncMock()
    handler.reap_expired_sessions.side_effect = [RuntimeError("db down"), 0, RuntimeError("db down again")]

    sleep_calls = []

    async def spy_sleep(seconds, *a, **kw):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 3:
            raise asyncio.CancelledError()

    monkeypatch.setattr("backend.reaper.asyncio.sleep", spy_sleep)

    task = asyncio.create_task(session_reaper_task(handler, interval_seconds=10))
    with pytest.raises(asyncio.CancelledError):
        await task

    # 1st failure -> backoff 10 (2^0). Then a success resets the counter.
    # 2nd failure (a fresh streak) -> backoff should be 10 again, not 20.
    assert sleep_calls[0] == 10          # first failure backoff
    assert sleep_calls[2] == 10          # counter reset after the success in between