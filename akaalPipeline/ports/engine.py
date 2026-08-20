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
    timeout_seconds: int = 300


@dataclass(frozen=True)
class EngineInvocationResult:
    invocation_id: str
    attempt_id: str
    lease_id: str
    fence_epoch: int
    is_success: bool
    initialization_fingerprint: Optional[str] = None
    graph_node_id: Optional[str] = None
    result_payload: Mapping[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())



@runtime_checkable
class CapabilityProbePort(Protocol):
    def probe_capability(self, capability_id: str) -> bool: ...


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
