"""Workflow Metadata, Step Definition, and Manifest Models."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple
from akaal.workflow.security.security_context import SecurityContext
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class WorkflowMetadata:
    """Immutable metadata describing a workflow definition."""

    workflow_id: str
    workflow_name: str
    version: str = "1.0.0"
    tenant_id: str = "default"
    created_at: str = "2026-01-01T00:00:00+00:00"
    requested_by: str = "system"
    correlation_id: str = "corr-default"
    trace_parent: str | None = None
    security_context: SecurityContext = field(default_factory=SecurityContext)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "version": self.version,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "requested_by": self.requested_by,
            "correlation_id": self.correlation_id,
            "trace_parent": self.trace_parent or "",
            "security_context": self.security_context.to_dict(),
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "version": self.version,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "requested_by": self.requested_by,
            "correlation_id": self.correlation_id,
            "trace_parent": self.trace_parent,
            "security_context": self.security_context.to_dict(),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class StepDefinition:
    """Immutable step definition specification."""

    step_id: str
    step_type: str
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    timeout_seconds: float = 300.0
    max_retries: int = 3
    execution_constraints: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "dependencies": list(self.dependencies),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "execution_constraints": dict(self.execution_constraints),
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "dependencies": list(self.dependencies),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "execution_constraints": dict(self.execution_constraints),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class WorkflowManifest:
    """Immutable full manifest specification for a workflow."""

    metadata: WorkflowMetadata
    step_definitions: Tuple[StepDefinition, ...]
    execution_graph: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    global_timeout_seconds: float = 3600.0
    max_retries: int = 3
    idempotency_key: str = "idemp-default"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        graph_dict = {k: list(v) for k, v in self.execution_graph.items()}
        payload = {
            "metadata": self.metadata.to_dict(),
            "step_definitions": [s.to_dict() for s in self.step_definitions],
            "execution_graph": graph_dict,
            "global_timeout_seconds": self.global_timeout_seconds,
            "max_retries": self.max_retries,
            "idempotency_key": self.idempotency_key,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "step_definitions": [s.to_dict() for s in self.step_definitions],
            "execution_graph": {k: list(v) for k, v in self.execution_graph.items()},
            "global_timeout_seconds": self.global_timeout_seconds,
            "max_retries": self.max_retries,
            "idempotency_key": self.idempotency_key,
            "checksum": self.checksum,
        }
