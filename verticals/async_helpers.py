"""Async utilities for running coroutines from sync or async contexts."""

import asyncio
import concurrent.futures


def run_async(coro, timeout: float = 60):
    """Run an async coroutine from any context (sync or already inside an event loop).

    When called from within a running event loop (e.g. a Jupyter notebook or
    an async test), a fresh event loop is spun up in a worker thread so the
    caller's loop is not blocked or re-entered.

    When called from a plain synchronous context, ``asyncio.run`` is used
    directly.

    Args:
        coro: The coroutine to run.
        timeout: Maximum seconds to wait for the result.

    Returns:
        The return value of the coroutine.
    """
    try:
        asyncio.get_running_loop()
        # Already inside a running loop — delegate to a thread.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=timeout)
    except RuntimeError:
        # No running loop — safe to call asyncio.run directly.
        return asyncio.run(coro)
