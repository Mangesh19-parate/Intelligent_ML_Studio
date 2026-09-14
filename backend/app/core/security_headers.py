from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from app.core.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production security headers & HTTPS enforcement middleware:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Enforces HTTPS redirection in production when X-Forwarded-Proto is http
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Enforce HTTPS in production if requested over plain HTTP behind reverse proxy
        if settings.ENV.lower() == "production":
            forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
            if forwarded_proto == "http":
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(url), status_code=301)

        response = await call_next(request)

        # 2. Inject standard OWASP security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.ENV.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
