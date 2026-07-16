import time
import threading

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_EXEMPT_PREFIXES = ("/api/v1/uploads", "/ws")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60, clean_interval: int = 300):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._clients: dict[str, list[float]] = {}
        self._last_clean = time.monotonic()
        self._clean_interval = clean_interval

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.window_seconds

        with self._lock:
            self._maybe_clean(now)
            entries = self._clients.setdefault(client_ip, [])
            entries[:] = [t for t in entries if now - t < window]

            if len(entries) >= self.max_requests:
                retry_after = int(window - (now - entries[0]))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(max(retry_after, 1))},
                )

            entries.append(now)

        return await call_next(request)

    def _maybe_clean(self, now: float) -> None:
        if now - self._last_clean < self._clean_interval:
            return
        self._last_clean = now
        expired = [
            ip for ip, entries in self._clients.items()
            if not entries or now - max(entries) > self.window_seconds * 2
        ]
        for ip in expired:
            del self._clients[ip]
