"""akaalPipeline.ports.engine
============================
Versioned abstract typing.Protocol ports for future akaalEngine integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class EngineInvocationRequest:
    contract_version: str
    binding_id: str
    correlation_id: str
    operation_id: str
    attempt_id: str
    invocation_id: str
    lease_id: str
    fence_epoch: int
    graph_node_id: str
    initialization_fingerprint: str
    payload: Mapping[str, Any]
    checkpoint_id: Optional[str] = None
    timeout_seconds: int = 300
    fencing_token_envelope: Optional[Mapping[str, Any]] = None
    execution_authorization_artifact: Optional[Mapping[str, Any]] = None



@dataclass(frozen=True)
class EngineInvocationResult:
    invocation_id: str
    attempt_id: str
    lease_id: str
    fence_epoch: int
    is_success: bool
    initialization_fingerprint: Optional[str] = None
    graph_node_id: Optional[str] = None
    binding_id: Optional[str] = None
    contract_version: Optional[str] = "1.0.0"
    result_payload: Mapping[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = False
    terminal: bool = True
    is_in_progress: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class CapabilityProbeResult:
    provider_id: str
    capability_id: str
    supported: bool
    is_healthy: bool = True
    proof_classification: Optional[str] = None
    reasons: Sequence[str] = field(default_factory=tuple)
    provider_version: Optional[str] = "1.0.0"


@runtime_checkable
class CapabilityProbePort(Protocol):
    def probe_capability(self, provider_id: str, capability_id: str) -> CapabilityProbeResult: ...


@runtime_checkable
class DiscoveryPort(Protocol):
    def discover_schema(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class AssessmentPort(Protocol):
    def assess_migration(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class PlanningPort(Protocol):
    def generate_plan(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class ExecutionPort(Protocol):
    def execute_task(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class CheckpointPort(Protocol):
    def verify_checkpoint(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class RecoveryPort(Protocol):
    def perform_recovery_action(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class ValidationPort(Protocol):
    def validate_data(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class ResourcePort(Protocol):
    def evaluate_resource_readiness(self, request: EngineInvocationRequest) -> EngineInvocationResult: ...


@runtime_checkable
class EventPort(Protocol):
    def publish_engine_event(self, event_data: Mapping[str, Any]) -> None: ...


@runtime_checkable
class SecretResolutionPort(Protocol):
    def resolve_secret_reference(self, secret_ref: str) -> str: ...
