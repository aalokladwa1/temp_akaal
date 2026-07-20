"""Sub-Context Domain Models for WorkflowContext Composition."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple
from akaal.workflow.security.security_context import SecurityContext
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Sub-context for execution progress, step tracking, and metrics."""
    
    workflow_id: str
    run_id: str
    completed_steps: Tuple[str, ...] = field(default_factory=tuple)
    pending_steps: Tuple[str, ...] = field(default_factory=tuple)
    retry_counts: Mapping[str, int] = field(default_factory=dict)
    checkpoint_reference: str | None = None
    step_metrics: Mapping[str, float] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(self.pending_steps),
            "retry_counts": dict(self.retry_counts),
            "checkpoint_reference": self.checkpoint_reference or "",
            "step_metrics": dict(self.step_metrics),
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(self.pending_steps),
            "retry_counts": dict(self.retry_counts),
            "checkpoint_reference": self.checkpoint_reference,
            "step_metrics": dict(self.step_metrics),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Sub-context for transient parameters, flags, and temporary state."""

    environment_variables: Mapping[str, str] = field(default_factory=dict)
    transient_parameters: Mapping[str, Any] = field(default_factory=dict)
    runtime_flags: Mapping[str, bool] = field(default_factory=dict)
    temporary_state: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "environment_variables": dict(self.environment_variables),
            "transient_parameters": dict(self.transient_parameters),
            "runtime_flags": dict(self.runtime_flags),
            "temporary_state": dict(self.temporary_state),
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_variables": dict(self.environment_variables),
            "transient_parameters": dict(self.transient_parameters),
            "runtime_flags": dict(self.runtime_flags),
            "temporary_state": dict(self.temporary_state),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class UserContext:
    """Sub-context for identity, security, tenant isolation, and tracing."""

    user_id: str = "system"
    tenant_id: str = "default"
    security_context: SecurityContext = field(default_factory=SecurityContext)
    granted_permissions: Tuple[str, ...] = field(default_factory=tuple)
    correlation_id: str = "correlation-default"
    trace_parent: str | None = None
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "security_context": self.security_context.to_dict(),
            "granted_permissions": list(self.granted_permissions),
            "correlation_id": self.correlation_id,
            "trace_parent": self.trace_parent or "",
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "security_context": self.security_context.to_dict(),
            "granted_permissions": list(self.granted_permissions),
            "correlation_id": self.correlation_id,
            "trace_parent": self.trace_parent,
            "checksum": self.checksum,
        }
