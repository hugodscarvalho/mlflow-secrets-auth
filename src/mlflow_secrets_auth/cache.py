"""TTL cache implementation for secrets.

Provides a lightweight, thread-safe cache with monotonic-clock–based TTLs and a
simple decorator (`cached_fetch`) to memoize zero-argument callables.

Design goals:
  * Monotonic time to avoid issues when the wall clock changes.
  * Thread safety via `RLock`.
  * No caching of failures: exceptions from the wrapped callable return `None`
    and are not stored.
  * Global cache instance for convenience, with helpers to clear and inspect size.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TTLCache:
    """Thread-safe TTL cache (monotonic-clock based)."""

    __slots__ = ("_cache", "_lock")

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> float:
        """Return a monotonically increasing timestamp."""
        return time.monotonic()

    def get(self, key: str) -> Any | None:
        """Get a value from the cache if present and not expired.

        Args:
            key: Cache key.

        Returns:
            The cached value if present and valid, otherwise None.

        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if self._now() > expiry:
                self._cache.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Set a value in the cache with a TTL.

        Non-positive TTLs are treated as "no caching" (the key is removed).

        Args:
            key: Cache key.
            value: Value to store.
            ttl_seconds: Time-to-live in seconds.

        """
        with self._lock:
            if ttl_seconds <= 0:
                self._cache.pop(key, None)
                return
            self._cache[key] = (value, self._now() + float(ttl_seconds))

    def delete(self, key: str) -> None:
        """Remove a key from the cache.

        Args:
            key: Cache key to remove.

        """
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with a prefix.

        Useful for provider-wide invalidation using e.g. ``f"{provider_name}:"``.

        Args:
            prefix: Prefix to match.

        """
        with self._lock:
            to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in to_delete:
                self._cache.pop(k, None)

    def size(self) -> int:
        """Return the current cache size, pruning expired entries first.

        Returns:
            Number of live (non-expired) entries.

        """
        with self._lock:
            now = self._now()
            to_delete = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in to_delete:
                self._cache.pop(k, None)
            return len(self._cache)


# Global cache instance
_global_cache = TTLCache()


def cached_fetch(cache_key: str, ttl_seconds: int) -> Callable[[Callable[[], T]], Callable[[], T | None]]:
    """Decorator to cache a zero-argument function's result with a TTL.

    Exceptions raised by the wrapped function are swallowed and result in `None`,
    which is not cached. Successful non-None results are cached.

    Args:
        cache_key: Unique cache key for the function result.
        ttl_seconds: Time-to-live for the cached value.

    Returns:
        A decorator that wraps a `Callable[[], T]` and returns `Callable[[], Optional[T]]`.

    """

    def decorator(fetch_func: Callable[[], T]) -> Callable[[], T | None]:
        def wrapper() -> T | None:
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                # Typing note: caller-provided T is preserved by construction.
                return cached_value  # type: ignore[return-value]

            try:
                value = fetch_func()
            except Exception:
                # Do not cache failures; return None to the caller.
                return None

            if value is not None:
                _global_cache.set(cache_key, value, ttl_seconds)
            return value

        return wrapper

    return decorator


def clear_cache() -> None:
    """Clear the global cache instance."""
    _global_cache.clear()


def delete_cache_key(key: str) -> None:
    """Remove a single cache entry by key.

    Args:
        key: Cache key to remove.

    """
    _global_cache.delete(key)


def get_cache_size() -> int:
    """Get the current size of the global cache (after pruning)."""
    return _global_cache.size()
