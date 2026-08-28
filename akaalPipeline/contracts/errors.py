"""akaalPipeline.contracts.errors
==============================
Structured pipeline exceptions and canonical security errors.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error
from akaalPipeline.contracts.enums import PipelineErrorCode


class PipelineError(Exception):
    """Base exception for all akaalPipeline domain errors."""

    def __init__(
        self,
        code: PipelineErrorCode,
        message: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
        correlation_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details) if details else {}
        self.correlation_id = correlation_id
        self.cause = cause

    def to_ipc_error(self) -> IPCError:
        category_map = {
            PipelineErrorCode.INVALID_REQUEST: IPCErrorCategory.INVALID_REQUEST,
            PipelineErrorCode.REVISION_CONFLICT: IPCErrorCategory.REVISION_CONFLICT,
            PipelineErrorCode.IDEMPOTENCY_CONFLICT: IPCErrorCategory.IDEMPOTENCY_CONFLICT,
            PipelineErrorCode.INVALID_TRANSITION: IPCErrorCategory.INVALID_REQUEST,
            PipelineErrorCode.UNBOUND: IPCErrorCategory.UNBOUND,
            PipelineErrorCode.UNAVAILABLE: IPCErrorCategory.UNAVAILABLE,
            PipelineErrorCode.UNSUPPORTED: IPCErrorCategory.UNSUPPORTED,
            PipelineErrorCode.INELIGIBLE: IPCErrorCategory.INELIGIBLE,
            PipelineErrorCode.NOT_READY: IPCErrorCategory.NOT_READY,
            PipelineErrorCode.POLICY_DENIED: IPCErrorCategory.FORBIDDEN,
            PipelineErrorCode.FORBIDDEN: IPCErrorCategory.FORBIDDEN,
            PipelineErrorCode.UNAUTHORIZED: IPCErrorCategory.UNAUTHORIZED,
            PipelineErrorCode.NOT_FOUND: IPCErrorCategory.NOT_FOUND,
            PipelineErrorCode.CONFLICT: IPCErrorCategory.CONFLICT,
            PipelineErrorCode.SOD_VIOLATION: IPCErrorCategory.FORBIDDEN,
            PipelineErrorCode.QUORUM_NOT_MET: IPCErrorCategory.FORBIDDEN,
            PipelineErrorCode.STALE_GENERATION: IPCErrorCategory.STALE_RESULT,
            PipelineErrorCode.SEAL_MISMATCH: IPCErrorCategory.FORBIDDEN,
            PipelineErrorCode.KEY_REVOKED: IPCErrorCategory.UNAUTHORIZED,
            PipelineErrorCode.CLOCK_SKEW_DETECTED: IPCErrorCategory.INTERNAL_ERROR,
            PipelineErrorCode.CSPRNG_UNAVAILABLE: IPCErrorCategory.INTERNAL_ERROR,
            PipelineErrorCode.CRYPTOGRAPHIC_DEPENDENCY_ERROR: IPCErrorCategory.INTERNAL_ERROR,
            PipelineErrorCode.LEASE_CONFLICT: IPCErrorCategory.INVALID_REQUEST,
            PipelineErrorCode.UNABLE_TO_ACQUIRE_LEASE: IPCErrorCategory.INVALID_REQUEST,
            PipelineErrorCode.STALE_RESULT: IPCErrorCategory.STALE_RESULT,
            PipelineErrorCode.CHECKPOINT_REJECTED: IPCErrorCategory.INVALID_REQUEST,
            PipelineErrorCode.CONTRACT_INCOMPATIBLE: IPCErrorCategory.PROTOCOL_INCOMPATIBLE,
            PipelineErrorCode.PERSISTENCE_FAILURE: IPCErrorCategory.INTERNAL_ERROR,
            PipelineErrorCode.INTERNAL_ERROR: IPCErrorCategory.INTERNAL_ERROR,
        }

        cat = category_map.get(self.code, IPCErrorCategory.INTERNAL_ERROR)
        return make_error(
            cat,
            code=self.code.value,
            message=self.message,
            details=self.details,
            correlation_id=self.correlation_id,
        )


class UnauthorizedError(PipelineError):
    def __init__(self, message: str = "Authentication required or credentials invalid.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.UNAUTHORIZED, message, correlation_id=correlation_id)


class ForbiddenError(PipelineError):
    def __init__(self, message: str = "Permission denied for requested action.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.FORBIDDEN, message, correlation_id=correlation_id)


class NotFoundError(PipelineError):
    def __init__(self, message: str = "Requested resource not found.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.NOT_FOUND, message, correlation_id=correlation_id)


class ConflictError(PipelineError):
    def __init__(self, message: str = "Conflict with current state.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.CONFLICT, message, correlation_id=correlation_id)


class SoDViolationError(PipelineError):
    def __init__(self, message: str = "Separation of Duties violation detected.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.SOD_VIOLATION, message, correlation_id=correlation_id)


class QuorumNotMetError(PipelineError):
    def __init__(self, message: str = "Required authorization quorum not met.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.QUORUM_NOT_MET, message, correlation_id=correlation_id)


class StaleGenerationError(PipelineError):
    def __init__(self, message: str = "Operation rejected due to stale generation / fencing epoch.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.STALE_GENERATION, message, correlation_id=correlation_id)


class SealMismatchError(PipelineError):
    def __init__(self, message: str = "Execution seal mismatch.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.SEAL_MISMATCH, message, correlation_id=correlation_id)


class KeyRevokedError(PipelineError):
    def __init__(self, message: str = "Cryptographic key has been revoked.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.KEY_REVOKED, message, correlation_id=correlation_id)


class ClockSkewDetectedError(PipelineError):
    def __init__(self, message: str = "Unacceptable clock skew detected.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.CLOCK_SKEW_DETECTED, message, correlation_id=correlation_id)


class CSPRNGUnavailableError(PipelineError):
    def __init__(self, message: str = "OS CSPRNG is unavailable.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.CSPRNG_UNAVAILABLE, message, correlation_id=correlation_id)


class RevisionConflictError(PipelineError):
    def __init__(self, message: str, expected_revision: int, actual_revision: int, correlation_id: Optional[str] = None) -> None:
        super().__init__(
            PipelineErrorCode.REVISION_CONFLICT,
            message,
            details={"expected_revision": expected_revision, "actual_revision": actual_revision},
            correlation_id=correlation_id,
        )


class IdempotencyConflictError(PipelineError):
    def __init__(self, message: str, idempotency_key: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(
            PipelineErrorCode.IDEMPOTENCY_CONFLICT,
            message,
            details={"idempotency_key": idempotency_key},
            correlation_id=correlation_id,
        )


class UnboundEngineError(PipelineError):
    def __init__(self, message: str = "No compatible akaalEngine port binding is registered.", correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.UNBOUND, message, correlation_id=correlation_id)


class UnavailableError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.UNAVAILABLE, message, correlation_id=correlation_id)


class UnsupportedModeError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.UNSUPPORTED, message, correlation_id=correlation_id)


class IneligibleError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.INELIGIBLE, message, correlation_id=correlation_id)


class NotReadyError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.NOT_READY, message, correlation_id=correlation_id)


class PolicyDeniedError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.POLICY_DENIED, message, correlation_id=correlation_id)


class LeaseConflictError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.LEASE_CONFLICT, message, correlation_id=correlation_id)


class UnableToAcquireLeaseError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.UNABLE_TO_ACQUIRE_LEASE, message, correlation_id=correlation_id)


class StaleResultError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.STALE_RESULT, message, correlation_id=correlation_id)


class CheckpointRejectedError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.CHECKPOINT_REJECTED, message, correlation_id=correlation_id)


class ContractIncompatibleError(PipelineError):
    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.CONTRACT_INCOMPATIBLE, message, correlation_id=correlation_id)


class PersistenceError(PipelineError):
    def __init__(self, message: str, cause: Optional[Exception] = None, correlation_id: Optional[str] = None) -> None:
        super().__init__(PipelineErrorCode.PERSISTENCE_FAILURE, message, cause=cause, correlation_id=correlation_id)


def make_pipeline_error(
    code: PipelineErrorCode,
    message: str,
    *,
    details: Optional[Mapping[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> PipelineError:
    return PipelineError(code, message, details=details, correlation_id=correlation_id)
