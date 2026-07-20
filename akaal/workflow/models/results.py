"""Step Status, Validation Result, and Workflow Step Result Models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple
from akaal.workflow.utils.serialization import compute_sha256


class StepStatus(str, Enum):
    """Execution status enum for an individual step."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Immutable result of pre/post-condition or structural contract validation."""

    valid: bool
    errors: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def success(cls, warnings: Tuple[str, ...] = ()) -> "ValidationResult":
        return cls(valid=True, errors=(), warnings=warnings)

    @classmethod
    def failure(cls, errors: Tuple[str, ...], warnings: Tuple[str, ...] = ()) -> "ValidationResult":
        return cls(valid=False, errors=errors, warnings=warnings)


@dataclass(frozen=True, slots=True)
class WorkflowStepResult:
    """Standardized result object returned by every workflow step execution."""

    step_id: str
    success: bool
    status: StepStatus
    duration_ms: float = 0.0
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    errors: Tuple[str, ...] = field(default_factory=tuple)
    metrics: Mapping[str, float] = field(default_factory=dict)
    artifacts: Mapping[str, str] = field(default_factory=dict)
    context_updates: Mapping[str, Any] = field(default_factory=dict)
    checkpoint_created: bool = False
    next_step_override: str | None = None
    retry_allowed: bool = True
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "step_id": self.step_id,
            "success": self.success,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metrics": dict(self.metrics),
            "artifacts": dict(self.artifacts),
            "context_updates": dict(self.context_updates),
            "checkpoint_created": self.checkpoint_created,
            "next_step_override": self.next_step_override or "",
            "retry_allowed": self.retry_allowed,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metrics": dict(self.metrics),
            "artifacts": dict(self.artifacts),
            "context_updates": dict(self.context_updates),
            "checkpoint_created": self.checkpoint_created,
            "next_step_override": self.next_step_override,
            "retry_allowed": self.retry_allowed,
            "checksum": self.checksum,
        }
