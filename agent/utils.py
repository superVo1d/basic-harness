"""Small shared helpers."""

from __future__ import annotations

import asyncio
import concurrent.futures


def run_sync(coro):
    """Run a coroutine from sync code, even inside a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # A loop is already running (CLI starts via asyncio.run) — run the
    # coroutine in its own thread with its own loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
