"""Exponential backoff retry decorator."""

import functools
import time

from .log import get_logger


def with_retry(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator: retry with exponential backoff on exception.

    Delays: base_delay * 2^attempt (2s -> 4s -> 8s by default).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                            func.__name__, attempt + 1, max_retries + 1, e, delay
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_retries + 1, e
                        )
            raise last_exc
        return wrapper
    return decorator
