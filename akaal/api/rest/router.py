"""
Main Version 1 Router (/api/v1).
"""

from fastapi import APIRouter
from akaal.api.rest.routers import (
    jobs,
    workflows,
    sessions,
    validation,
    reporting,
    operations,
    schema,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(jobs.router)
v1_router.include_router(workflows.router)
v1_router.include_router(sessions.router)
v1_router.include_router(validation.router)
v1_router.include_router(reporting.router)
v1_router.include_router(operations.router)
v1_router.include_router(schema.router)
