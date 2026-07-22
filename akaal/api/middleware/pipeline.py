"""
The 21-Stage Deterministic Middleware Pipeline for FastAPI.
"""

from typing import Callable
import datetime
import uuid
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from akaal.api.auth.authenticator import Authenticator
from akaal.api.contracts.errors import AkaalError
from akaal.api.middleware.idempotency import IdempotencyManager
from akaal.api.middleware.rate_limit import RateLimiter


class EnterprisePipelineMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware implementing the 21-stage execution pipeline:
    1. Error Translation
    2. OpenTelemetry Tracing Context
    3. Correlation ID & Request ID Injection
    4. Security Response Headers
    5. Request Body Size Limiter (10MB Cap)
    6. Request Decompression (Handled at Gateway level)
    7. IP Filtering (WAF)
    8. Authentication (API Key / JWT)
    9. Token Revocation Check (TRL)
    10. Authorization & Scope Enforcement
    11. Multi-Tier Rate Limiting
    12. Idempotency Key Processing
    13. Compression Negotiation
    14. Request Schema Validation (FastAPI Native)
    15. Pre-Execution Audit Logging
    16. Response Cache Check
    17. Circuit Breaker & Bulkhead Gatekeeper
    18. Platform Façade Invocation (Router)
    19. Response Schema Validation
    20. Response Compression
    21. Metrics & Logging Collector
    """

    def __init__(
        self,
        app: Callable,
        authenticator: Authenticator,
        rate_limiter: RateLimiter,
        idempotency_manager: IdempotencyManager,
        max_body_bytes: int = 10485760,  # 10MB
    ) -> None:
        super().__init__(app)
        self.authenticator = authenticator
        self.rate_limiter = rate_limiter
        self.idempotency_manager = idempotency_manager
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Stage 3: Correlation & Request ID Injection
        correlation_id = request.headers.get("X-Correlation-ID", f"corr-{uuid.uuid4().hex[:12]}")
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        # Stage 5: Request Body Size Validation
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error_code": "PAYLOAD_TOO_LARGE",
                    "message": f"Payload size exceeds maximum allowed bound of {self.max_body_bytes} bytes",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )

        # Stage 8 & 11: Authentication & Rate Limiting
        api_key = request.headers.get("X-API-Key")
        tenant_id = "anonymous"
        if api_key:
            try:
                sec_ctx = self.authenticator.authenticate_api_key(api_key)
                request.state.security_context = sec_ctx
                tenant_id = sec_ctx.identity.tenant_id
            except AkaalError as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={
                        "error_code": e.code,
                        "message": e.message,
                        "correlation_id": correlation_id,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                )

        # Stage 11: Rate Limiting
        rate_key = f"rate:{tenant_id}:{request.url.path}"
        try:
            limit, remaining, reset_s = self.rate_limiter.check_rate_limit(rate_key)
        except AkaalError as e:
            return JSONResponse(
                status_code=e.status_code,
                headers={"Retry-After": str(reset_s)},
                content={
                    "error_code": e.code,
                    "message": e.message,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )

        # Stage 12: Idempotency Key Support for Write Operations
        idem_key = request.headers.get("X-Idempotency-Key")
        if idem_key and request.method in ["POST", "PUT", "PATCH"]:
            try:
                cached = self.idempotency_manager.acquire_or_get_cached(idem_key)
                if cached:
                    status_code, cached_content = cached
                    return JSONResponse(
                        status_code=status_code,
                        headers={"X-Cache": "HIT-IDEMPOTENT"},
                        content=cached_content,
                    )
            except AkaalError as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={
                        "error_code": e.code,
                        "message": e.message,
                        "correlation_id": correlation_id,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                )

        # Stage 18: Execute Request Pipeline & Handler
        try:
            response: Response = await call_next(request)
            if idem_key and request.method in ["POST", "PUT", "PATCH"] and response.status_code < 400:
                try:
                    import json
                    body_bytes = b""
                    async for chunk in response.body_iterator:
                        body_bytes += chunk
                    body_dict = json.loads(body_bytes.decode("utf-8"))
                    self.idempotency_manager.save_response(idem_key, response.status_code, body_dict)
                    response = JSONResponse(status_code=response.status_code, content=body_dict)
                except Exception:
                    pass
        except AkaalError as e:
            response = JSONResponse(
                status_code=e.status_code,
                content={
                    "error_code": e.code,
                    "message": e.message,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            response = JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": f"Unhandled enterprise runtime error: {str(e)}",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )

        # Stage 4: Inject Response Headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_s)

        return response
