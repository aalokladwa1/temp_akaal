"""
akaalEngine.gateway.models.responses
====================================
Canonical normalized Gateway response wrapper.
Surfaces execution status, payload, failure categories, and proof metadata while protecting secret boundaries.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class GatewayResponse(Generic[T]):
    """Normalized response envelope returned by EngineGateway for all operations."""
    operation_id: str
    operation_type: str
    migration_id: str
    run_id: str
    success: bool
    status_code: str
    payload: Optional[T] = None
    failure_category: Optional[str] = None
    error_message: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    retryable: bool = False
    terminal: bool = True
    fencing_epoch: Optional[int] = None
    executed_at: float = field(default_factory=time.time)
    proof_classification: Optional[str] = None

    @classmethod
    def create_success(
        cls,
        operation_id: str,
        operation_type: str,
        migration_id: str,
        run_id: str,
        payload: T,
        fencing_epoch: Optional[int] = None,
        proof_classification: Optional[str] = None,
    ) -> "GatewayResponse[T]":
        """Constructs a successful GatewayResponse."""
        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            migration_id=migration_id,
            run_id=run_id,
            success=True,
            status_code="SUCCESS",
            payload=payload,
            fencing_epoch=fencing_epoch,
            proof_classification=proof_classification,
        )

    @classmethod
    def create_failure(
        cls,
        operation_id: str,
        operation_type: str,
        migration_id: str,
        run_id: str,
        failure_category: str,
        error_message: str,
        reasons: Optional[List[str]] = None,
        retryable: bool = False,
        terminal: bool = True,
        fencing_epoch: Optional[int] = None,
    ) -> "GatewayResponse[T]":
        """Constructs a failed GatewayResponse."""
        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            migration_id=migration_id,
            run_id=run_id,
            success=False,
            status_code=failure_category,
            payload=None,
            failure_category=failure_category,
            error_message=error_message,
            reasons=reasons or [error_message],
            retryable=retryable,
            terminal=terminal,
            fencing_epoch=fencing_epoch,
        )
