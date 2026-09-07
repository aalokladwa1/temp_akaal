"""akaalEngine.intelligence.models.errors
=========================================
Typed error hierarchy for the P7C.1 Intelligence Kernel. No bare Exception is ever
raised by production kernel code -- every failure mode below is a distinct, catchable
type so callers (akaalPipeline command/query handlers) can map it to the correct IPC
error category rather than collapsing everything into INTERNAL_ERROR.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class IntelligenceError(Exception):
    """Base class for every P7C.1 Intelligence Kernel error."""

    code = "INTELLIGENCE_ERROR"

    def __init__(self, message: str, *, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details) if details else {}


class IntelligenceValidationError(IntelligenceError):
    """Raised when an IntelligenceRequest/IntelligenceContext fails structural or
    semantic validation (e.g. missing tenant, malformed task, mismatched context)."""

    code = "INTELLIGENCE_VALIDATION_ERROR"


class IntelligenceTaskUnsupportedError(IntelligenceError):
    """Raised when no producer is registered for the requested IntelligenceTask.
    The kernel never fabricates a result for a task it cannot genuinely compute."""

    code = "INTELLIGENCE_TASK_UNSUPPORTED"


class IntelligenceNotFoundError(IntelligenceError):
    """Raised when a referenced artifact does not exist."""

    code = "INTELLIGENCE_ARTIFACT_NOT_FOUND"


class IntelligenceStaleArtifactError(IntelligenceError):
    """Raised when a caller attempts a consequential operation (e.g. ACCEPT) against
    an artifact whose context fingerprint no longer matches current canonical state."""

    code = "INTELLIGENCE_ARTIFACT_STALE"


class IntelligenceInvalidTransitionError(IntelligenceError):
    """Raised when a requested lifecycle transition is not permitted from the
    artifact's current lifecycle state."""

    code = "INTELLIGENCE_INVALID_LIFECYCLE_TRANSITION"


class IntelligenceCancelledError(IntelligenceError):
    """Raised when a request is cancelled (caller-initiated or budget-driven) before
    completion. Distinct from IntelligenceBudgetExceededError so callers can tell
    voluntary cancellation apart from involuntary budget exhaustion."""

    code = "INTELLIGENCE_CANCELLED"


class IntelligenceBudgetExceededError(IntelligenceError):
    """Raised when a request exceeds its configured time/resource budget. Budget
    exhaustion must produce this typed, bounded failure -- never an indefinite hang,
    silent truncation, or fabricated completion."""

    code = "INTELLIGENCE_BUDGET_EXCEEDED"


class IntelligenceTenantBoundaryError(IntelligenceError):
    """Raised when a request/context tenant dimension does not match the resource
    being addressed. Mirrors akaalPipeline.contracts.errors.PipelineError's
    TENANT_BOUNDARY_VIOLATION discipline: this is the kernel-local defensive check,
    not a substitute for canonical PipelineActorContext.enforce_resource_scope()."""

    code = "INTELLIGENCE_TENANT_BOUNDARY_VIOLATION"
