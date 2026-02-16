"""Rate limiting and error handling middleware for Lore Cloud Server."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install lore-sdk[server]")

logger = logging.getLogger(__name__)

# ── Rate Limiter ───────────────────────────────────────────────────

# Default: 100 requests per 60 seconds
DEFAULT_RATE_LIMIT = 100
DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    """In-memory sliding window rate limiter per API key."""

    def __init__(
        self,
        max_requests: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # key_identifier -> list of request timestamps (monotonic)
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """Check if a request is allowed for the given key.

        Returns (allowed, retry_after_seconds).
        """
        now = time.monotonic()
        window_start = now - self.window_seconds
        timestamps = self._requests[key]

        # Prune old entries
        while timestamps and timestamps[0] < window_start:
            timestamps.pop(0)

        if len(timestamps) >= self.max_requests:
            # Calculate retry-after from oldest request in window
            retry_after = int(timestamps[0] - window_start) + 1
            if retry_after < 1:
                retry_after = 1
            return False, retry_after

        timestamps.append(now)
        return True, 0

    def clear(self) -> None:
        """Clear all rate limit state (for testing)."""
        self._requests.clear()


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Replace the global rate limiter (for testing/config)."""
    global _rate_limiter
    _rate_limiter = limiter


# ── Middleware ─────────────────────────────────────────────────────

# Max request body size: 1MB
MAX_BODY_SIZE = 1_048_576


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and structured logging context, collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import uuid
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        response.headers["X-Request-Id"] = request_id

        # Collect HTTP metrics (skip /metrics and /health to avoid noise)
        path = request.url.path
        if path not in ("/metrics", "/health"):
            try:
                from lore.server.config import settings as _s
                from lore.server.metrics import http_request_duration, http_requests_total
                if _s.metrics_enabled:
                    http_requests_total.inc(method=request.method, path=path, status=str(response.status_code))
                    http_request_duration.observe(duration, method=request.method, path=path)
            except Exception:
                pass

        # Structured request logging
        req_logger = logging.getLogger("lore.server.access")
        req_logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "latency_ms": round(duration * 1000, 2),
                "org_id": getattr(getattr(request, "state", None), "org_id", None),
            },
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting based on the API key in the Authorization header."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract API key for rate limiting
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
            limiter = get_rate_limiter()
            allowed, retry_after = limiter.is_allowed(key)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry later.",
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding MAX_BODY_SIZE."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "request_too_large",
                            "message": f"Request body exceeds {MAX_BODY_SIZE} bytes.",
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


# ── Error Handlers ─────────────────────────────────────────────────


def install_error_handlers(app: FastAPI) -> None:
    """Install global exception handlers for consistent JSON error responses."""

    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Map status codes to error codes
        error_codes = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            413: "request_too_large",
            422: "validation_error",
            429: "rate_limit_exceeded",
        }
        error_code = error_codes.get(exc.status_code, "error")
        message = str(exc.detail) if exc.detail else f"HTTP {exc.status_code}"

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_code, "message": message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Check if this is a JSON decode error (malformed JSON)
        for error in exc.errors():
            if error.get("type") == "json_invalid":
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "malformed_json",
                        "message": "Request body contains invalid JSON.",
                    },
                )

        # Regular validation errors
        messages = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            messages.append(f"{loc}: {error['msg']}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "; ".join(messages),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An internal server error occurred.",
            },
        )


def install_middleware(app: FastAPI) -> None:
    """Install all middleware on the app."""
    # Order matters: outermost runs first (added last)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
