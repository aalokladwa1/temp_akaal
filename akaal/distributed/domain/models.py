"""
Enterprise Shared Domain Models for Distributed Runtime (Platform 2).
All models are strictly immutable and enforce fail-fast invariant validation on construction.
"""

from dataclasses import dataclass, field, replace
from typing import Dict, Any, Optional, List, Set
import uuid

from akaal.distributed.domain.identifiers import (
    WorkerId,
    NodeId,
    ClusterId,
    TaskId,
    ExecutionId,
    AttemptId,
    LeaseId,
    CorrelationId,
    ReservationId,
    IdempotencyKey,
)
from akaal.distributed.domain.enums import (
    WorkerStatus,
    WorkerHealth,
    ClusterState,
    AssignmentState,
)
from akaal.distributed.domain.errors import DomainValidationError


@dataclass(frozen=True)
class WorkerCapability:
    name: str
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise DomainValidationError("WorkerCapability name must be a non-empty string.")


@dataclass(frozen=True)
class CustomResource:
    name: str
    quantity: float
    unit: str = ""

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise DomainValidationError("CustomResource name must be a non-empty string.")
        if self.quantity < 0:
            raise DomainValidationError("CustomResource quantity must be non-negative.")


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_cores: float = 1.0
    memory_mb: float = 1024.0
    queue_capacity: int = 100
    concurrency_limit: int = 10
    disk_io_mbps: float = 100.0
    network_mbps: float = 1000.0
    custom_resources: Dict[str, CustomResource] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cpu_cores < 0 or self.memory_mb < 0 or self.concurrency_limit < 0:
            raise DomainValidationError("ResourceSnapshot quantities must be non-negative.")


@dataclass(frozen=True)
class ResourceReservation:
    reservation_id: ReservationId
    worker_id: WorkerId
    cpu_cores: float
    memory_mb: float
    concurrency: int
    created_at: float
    expires_at: float

    def __post_init__(self) -> None:
        if self.expires_at <= self.created_at:
            raise DomainValidationError("ResourceReservation expiration must be strictly after creation timestamp.")
        if self.cpu_cores < 0 or self.memory_mb < 0 or self.concurrency < 0:
            raise DomainValidationError("ResourceReservation resource amounts must be non-negative.")


@dataclass(frozen=True)
class Worker:
    worker_id: WorkerId
    node_id: NodeId
    worker_version: str = "1.0.0"
    status: WorkerStatus = WorkerStatus.REGISTERED
    health: WorkerHealth = WorkerHealth.HEALTHY
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[WorkerCapability] = field(default_factory=list)
    capacity: int = 10
    current_load: int = 0
    resources: ResourceSnapshot = field(default_factory=ResourceSnapshot)
    registration_timestamp: float = 0.0
    last_heartbeat: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity < 0:
            raise DomainValidationError("Worker capacity must be non-negative.")
        if self.current_load < 0:
            raise DomainValidationError("Worker current_load must be non-negative.")
        if not isinstance(self.status, WorkerStatus):
            raise DomainValidationError("Invalid WorkerStatus.")
        if not isinstance(self.health, WorkerHealth):
            raise DomainValidationError("Invalid WorkerHealth.")


@dataclass(frozen=True)
class Node:
    node_id: NodeId
    hostname: str
    ip_address: str
    max_workers: int = 16
    status: str = "ACTIVE"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hostname or not isinstance(self.hostname, str):
            raise DomainValidationError("Node hostname must be a non-empty string.")
        if self.max_workers < 1:
            raise DomainValidationError("Node max_workers must be at least 1.")


@dataclass(frozen=True)
class Cluster:
    cluster_id: ClusterId
    name: str
    state: ClusterState = ClusterState.INITIALIZING
    leader_node_id: Optional[NodeId] = None
    cluster_version: int = 1
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if self.cluster_version < 1:
            raise DomainValidationError("Cluster version must be at least 1.")


@dataclass(frozen=True)
class Task:
    task_id: TaskId
    execution_id: ExecutionId
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 10
    required_capabilities: List[str] = field(default_factory=list)
    preferred_capabilities: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    min_worker_version: str = "1.0.0"
    retry_count: int = 0
    max_retries: int = 3
    delay_seconds: float = 0.0
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise DomainValidationError("Task name must be a non-empty string.")
        if self.max_retries < 0 or self.retry_count < 0:
            raise DomainValidationError("Task retry counts must be non-negative.")


@dataclass(frozen=True)
class Lease:
    lease_id: LeaseId
    owner_worker_id: WorkerId
    task_id: TaskId
    created_at: float
    expires_at: float
    ttl_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.expires_at <= self.created_at:
            raise DomainValidationError("Lease expiration must be strictly after creation timestamp.")
        if self.ttl_seconds <= 0:
            raise DomainValidationError("Lease ttl_seconds must be positive.")


@dataclass(frozen=True)
class ExecutionToken:
    execution_id: ExecutionId
    attempt_id: AttemptId
    lease_id: LeaseId
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not self.execution_id or not self.attempt_id or not self.lease_id or not self.correlation_id:
            raise DomainValidationError("ExecutionToken must contain all required identifiers.")


@dataclass(frozen=True)
class Assignment:
    task_id: TaskId
    worker_id: WorkerId
    lease: Lease
    state: AssignmentState = AssignmentState.ASSIGNED
    assigned_at: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.state, AssignmentState):
            raise DomainValidationError("Invalid AssignmentState.")


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: ExecutionId
    correlation_id: CorrelationId
    task: Task
    idempotency_key: IdempotencyKey
    submitted_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.execution_id or not self.correlation_id or not self.idempotency_key:
            raise DomainValidationError("ExecutionRequest must contain execution_id, correlation_id, and idempotency_key.")


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: ExecutionId
    attempt_id: AttemptId
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise DomainValidationError("ExecutionResult duration_seconds must be non-negative.")


@dataclass(frozen=True)
class Heartbeat:
    worker_id: WorkerId
    node_id: NodeId
    timestamp: float
    health: WorkerHealth = WorkerHealth.HEALTHY
    current_load: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.current_load < 0:
            raise DomainValidationError("Heartbeat current_load must be non-negative.")


@dataclass(frozen=True)
class ClusterMembership:
    cluster_id: ClusterId
    nodes: Dict[str, Node] = field(default_factory=dict)
    workers: Dict[str, Worker] = field(default_factory=dict)
    quorum_size: int = 1
    cluster_version: int = 1

    def __post_init__(self) -> None:
        if self.quorum_size < 1:
            raise DomainValidationError("ClusterMembership quorum_size must be at least 1.")
        if self.cluster_version < 1:
            raise DomainValidationError("ClusterMembership cluster_version must be at least 1.")


@dataclass(frozen=True)
class SchedulerDecision:
    task_id: TaskId
    target_worker_id: Optional[WorkerId]
    policy_name: str
    decision_reason: str
    decision_timestamp: float


@dataclass(frozen=True)
class ClusterSnapshot:
    cluster_id: ClusterId
    state: ClusterState
    leader_node_id: Optional[NodeId]
    membership: ClusterMembership
    snapshot_version: int
    timestamp: float

    def __post_init__(self) -> None:
        if self.snapshot_version < 1:
            raise DomainValidationError("ClusterSnapshot snapshot_version must be at least 1.")
