"""
services/rate_limit.py -- a small in-memory sliding-window limiter. No Redis needed at
this scale (single process, $0 stack) -- the window is a deque of timestamps per key,
trimmed on every check. Good enough to prove the pattern; a multi-process deployment
would move this to Redis, noted as a limitation in the README.
"""
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Optional


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Returns True if this call is within the limit (and records it), False if the
        caller is over the limit (and does NOT record it -- rejected calls don't count
        against the window further)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


# Two limiters: a per-IP ceiling (protects against one flooding source) and a per-widget
# ceiling (protects a single widget from being the sole target even from many IPs).
per_ip_limiter = RateLimiter(max_requests=10, window_seconds=10)
per_widget_limiter = RateLimiter(max_requests=30, window_seconds=10)
