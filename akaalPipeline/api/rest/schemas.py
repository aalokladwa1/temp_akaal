"""
akaalPipeline.api.rest.schemas
==============================
Versioned, stable public Pydantic models for the Enterprise REST Platform (/api/v1/...).
Prevents leakage of internal database structures, private dataclasses, or stack traces.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field


class CreateMigrationRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=256, description="Human-readable migration name.")
    mode: str = Field(default="M1", description="Execution mode: M1, M2, M3, M4, M5, M6, M7, M8.")
    configuration: Optional[dict[str, Any]] = Field(default_factory=dict, description="Configuration options.")


class CancelMigrationRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: Optional[int] = Field(default=None, ge=1, description="Optimistic concurrency fence.")


class MigrationResponseV1(BaseModel):
    model_config = ConfigDict(extra="ignore")

    migration_id: str
    revision: int
    name: str
    mode: str
    state: str
    tenant_id: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    created_at: str
    updated_at: str


class MigrationListResponseV1(BaseModel):
    migrations: Sequence[MigrationResponseV1]
    limit: int
    offset: int
    total: int
    next_offset: Optional[int] = None


class OperationResponseV1(BaseModel):
    model_config = ConfigDict(extra="ignore")

    operation_id: str
    operation_type: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ErrorDetailV1(BaseModel):
    code: str
    message: str
    category: str
    retryable: bool
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
