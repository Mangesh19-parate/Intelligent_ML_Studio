import time
import ipaddress
import threading
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status


def is_ip_in_trusted_proxies(ip_str: str, trusted_list: list[str]) -> bool:
    """Checks if an IP address belongs to explicitly configured trusted proxies or loopback."""
    if not ip_str or ip_str in ("unknown", "testclient"):
        return True
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_loopback:
            return True
        for trusted in trusted_list:
            if not trusted:
                continue
            if "/" in trusted:
                if ip_obj in ipaddress.ip_network(trusted, strict=False):
                    return True
            elif ip_str == trusted:
                return True
    except ValueError:
        if ip_str in ("localhost", "127.0.0.1", "::1"):
            return True
    return False


def get_trusted_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """
    Derives real client IP safely.
    Only trusts X-Forwarded-For headers if the immediate upstream client connection
    originates from a verified trusted proxy / local proxy network.
    """
    direct_host = request.client.host if request.client else "127.0.0.1"
    
    if is_ip_in_trusted_proxies(direct_host, trusted_proxies):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if ips:
                return ips[0]
    return direct_host


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter using collections.deque.
    Complexity:
      - Check/Record: Amortized O(1) time per request (each timestamp is pushed once and popped once).
      - Memory: O(R) where R is active request volume in sliding window across all active keys.
    Protects auth and inference endpoints against brute-force attacks and volumetric floods.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Maps key -> deque of monotonic timestamps
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.time()

    def _cleanup(self, current_time: float, max_window: float = 3600.0):
        if current_time - self._last_cleanup > 300.0:
            stale_cutoff = current_time - max_window
            for key in list(self._requests.keys()):
                timestamps = self._requests[key]
                while timestamps and timestamps[0] <= stale_cutoff:
                    timestamps.popleft()
                if not timestamps:
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
            
            # Amortized O(1) eviction of expired timestamps from the left
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                oldest_in_window = timestamps[0]
                retry_after = int(window_seconds - (current_time - oldest_in_window)) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Too many attempts. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            timestamps.append(current_time)


# Global singleton instance
auth_rate_limiter = SlidingWindowRateLimiter()


def rate_limit_auth(
    max_requests: int = 5,
    window_seconds: int = 60,
):
    """
    FastAPI dependency for rate-limiting requests per verified client IP.
    Automatically bypasses in testing environment unless 'x-enforce-rate-limit' header is set.
    """
    from app.core.config import settings

    async def dependency(request: Request):
        if settings.ENV.lower() == "testing" and not request.headers.get("x-enforce-rate-limit"):
            return

        trusted_proxies = settings.TRUSTED_PROXIES if isinstance(settings.TRUSTED_PROXIES, list) else ["127.0.0.1", "::1"]
        client_ip = get_trusted_client_ip(request, trusted_proxies)
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"
        auth_rate_limiter.check_rate_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
    return dependency
