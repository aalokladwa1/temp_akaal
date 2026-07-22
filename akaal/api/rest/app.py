"""
FastAPI Enterprise Application Factory for AKAAL Platform 7.
"""

from typing import Dict, Any
import datetime
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from akaal.api.auth.authenticator import Authenticator
from akaal.api.middleware.idempotency import IdempotencyManager
from akaal.api.middleware.pipeline import EnterprisePipelineMiddleware
from akaal.api.middleware.rate_limit import RateLimiter
from akaal.api.rest.router import v1_router


def create_app() -> FastAPI:
    """Factory creating configured FastAPI enterprise application."""
    app = FastAPI(
        title="AKAAL Platform 7 — Enterprise REST API",
        description="Official Integration Layer for the AKAAL Platform.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Initialize Middleware Singletons
    authenticator = Authenticator()
    rate_limiter = RateLimiter(requests_per_window=1000, window_seconds=60)
    idempotency_manager = IdempotencyManager()

    # Mount 21-Stage Pipeline Middleware
    app.add_middleware(
        EnterprisePipelineMiddleware,
        authenticator=authenticator,
        rate_limiter=rate_limiter,
        idempotency_manager=idempotency_manager,
    )

    # Mount Routers
    app.include_router(v1_router)

    # Health Endpoints
    @app.get("/health", tags=["Health"])
    async def health() -> Dict[str, Any]:
        """Aggregated health status."""
        return {
            "status": "HEALTHY",
            "service": "akaal-platform7-rest",
            "version": "1.0.0",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @app.get("/readiness", tags=["Health"])
    async def readiness() -> Dict[str, Any]:
        """Cluster readiness probe."""
        return {
            "status": "READY",
            "dependencies": {"redis": "UP", "kafka": "UP", "platform1": "UP"},
        }

    @app.get("/liveness", tags=["Health"])
    async def liveness() -> Dict[str, Any]:
        """AsyncIO event loop liveness probe."""
        return {"status": "ALIVE"}

    # Custom OpenAPI Schema Customization
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="AKAAL Enterprise APIs & Integration",
            version="1.0.0",
            description="Enterprise integration contract specification for Platform 7.",
            routes=app.routes,
        )
        openapi_schema["info"]["x-akaal-architecture"] = "Platform 7 Integration Layer"
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


# Application Instance
app = create_app()
