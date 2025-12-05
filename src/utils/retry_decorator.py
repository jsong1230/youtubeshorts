"""
Retry decorator with exponential backoff for handling transient failures.
"""

import time
import random
import functools
from typing import Callable, Tuple, Type, TypeVar, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = TypeVar(
    "P"
)  # Using TypeVar for arguments since ParamSpec might be too strict for some users, or use Any


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exceptions: Tuple of exception types to catch and retry (default: (Exception,))
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        jitter: Add random jitter to prevent thundering herd (default: True)

    Example:
        @retry(max_retries=3, base_delay=1, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor**attempt), max_delay)

                    # Add jitter (random 0-25% of delay)
                    if jitter:
                        delay = delay * (0.75 + random.random() * 0.25)

                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    logger.info(f"   Retrying in {delay:.2f} seconds...")

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def retry_on_rate_limit(
    max_retries: int = 5, base_delay: float = 2.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Specialized retry decorator for API rate limits.
    Uses longer delays and more retries.

    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Initial delay in seconds (default: 2.0)
    """
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=120.0,
        exceptions=(Exception,),  # Catch all for rate limits
        backoff_factor=2.0,
        jitter=True,
    )
