"""
Structured Logging Middleware with Correlation IDs (P1.5).
Formats request/response logs as JSON with request_id, path, status, and duration_ms.
"""

import time
import uuid
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("ml_studio.access")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_entry = {
                "timestamp": time.time(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else "unknown",
            }
            if status_code >= 500:
                logger.error(json.dumps(log_entry))
            else:
                logger.info(json.dumps(log_entry))
