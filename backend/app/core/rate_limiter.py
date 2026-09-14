import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException, status

class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter for sensitive authentication endpoints.
    Protects against brute-force attacks and credential stuffing.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Maps key -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup(self, current_time: float, max_window: float = 3600.0):
        if current_time - self._last_cleanup > 300.0:
            stale_cutoff = current_time - max_window
            for key in list(self._requests.keys()):
                self._requests[key] = [t for t in self._requests[key] if t > stale_cutoff]
                if not self._requests[key]:
                    del self._requests[key]
            self._last_cleanup = current_time

    def check_rate_limit(
        self,
        key: str,
        max_requests: int = 5,
        window_seconds: int = 60,
    ) -> None:
        current_time = time.time()
        window_start = current_time - window_seconds

        with self._lock:
            self._cleanup(current_time)
            timestamps = self._requests[key]
            # Remove timestamps outside the sliding window
            self._requests[key] = [t for t in timestamps if t > window_start]

            if len(self._requests[key]) >= max_requests:
                oldest_in_window = self._requests[key][0]
                retry_after = int(window_seconds - (current_time - oldest_in_window)) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Too many attempts. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            self._requests[key].append(current_time)


# Global singleton instance
auth_rate_limiter = SlidingWindowRateLimiter()

def rate_limit_auth(
    max_requests: int = 5,
    window_seconds: int = 60,
):
    """
    FastAPI dependency for rate-limiting authentication requests per client IP.
    """
    async def dependency(request: Request):
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or request.client.host
            if request.client
            else "unknown"
        )
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"
        auth_rate_limiter.check_rate_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
    return dependency
