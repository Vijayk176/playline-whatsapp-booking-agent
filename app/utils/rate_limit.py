import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

WINDOW_SECONDS = 60
MAX_REQUESTS = 120

_hits = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _hits[client_ip]
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()

        if len(window) >= MAX_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})

        window.append(now)
        return await call_next(request)
