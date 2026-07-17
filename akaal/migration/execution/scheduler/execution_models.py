from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from asyncio import Event
from typing import Dict, Tuple, Any, Optional, Protocol, List

class TaskState(str, Enum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    READY = "READY"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RECOVERY_UNKNOWN = "RECOVERY_UNKNOWN"

class ConcurrencyPolicy(str, Enum):
    WAVE_BASED = "WAVE_BASED"
    DYNAMIC_FLOW = "DYNAMIC_FLOW"

class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    CRASHED = "CRASHED"
    TERMINATED = "TERMINATED"

class SchedulerLifecycleState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

@dataclass(frozen=True)
class TaskExecutionContext:
    session_id: str
    start_time: datetime
    cancellation_event: Event

@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskState
    error_message: Optional[str] = None
    execution_duration_ms: float = 0.0

class SchedulableOperation(Protocol):
    async def execute(self, context: TaskExecutionContext) -> TaskResult:
        ...

@dataclass(frozen=True)
class SchedulerConfiguration:
    session_id: str
    max_workers: int
    retry_limit: int
    retry_backoff_seconds: float
    concurrency_policy: ConcurrencyPolicy
    starvation_timeout_seconds: float = 30.0
    queue_max_size: int = 10000

    def validate(self) -> None:
        if not self.session_id:
            raise ValueError("session_id cannot be empty.")
        if self.max_workers < 1 or self.max_workers > 64:
            raise ValueError("Max workers must be between 1 and 64.")
        if self.retry_limit < 0 or self.retry_limit > 5:
            raise ValueError("Retry limit must be between 0 and 5.")
        if self.retry_backoff_seconds < 0.1 or self.retry_backoff_seconds > 60.0:
            raise ValueError("Retry backoff must be between 0.1 and 60.0 seconds.")
        if self.starvation_timeout_seconds <= 0:
            raise ValueError("starvation_timeout_seconds must be positive.")
        if self.queue_max_size < 1:
            raise ValueError("queue_max_size must be positive.")

@dataclass
class SchedulerMetrics:
    queue_depth: int = 0
    peak_queue_depth: int = 0
    worker_utilization_percent: float = 0.0
    throughput_tps: float = 0.0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    retry_count: int = 0
    skipped_count: int = 0
    cancelled_count: int = 0
    scheduler_uptime_seconds: float = 0.0
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    active_workers: int = 0

@dataclass
class SchedulerHealth:
    is_healthy: bool = True
    last_diagnosed: Optional[datetime] = None
    deadlock_detected: bool = False
    starvation_warning: bool = False

@dataclass(frozen=True)
class SchedulerCheckpoint:
    session_id: str
    completed_task_ids: Tuple[str, ...]
    in_flight_task_ids: Tuple[str, ...]
    retry_counts: Dict[str, int]
    graph_hash: str
    configuration_hash: str
    schema_version: str
    timestamp: datetime
    checksum: str = ""

@dataclass
class SchedulableTask:
    task_id: str
    operation_ref: SchedulableOperation
    idempotency_key: str
    priority: int
    dependencies: Tuple[str, ...]
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 300.0
    state: TaskState = TaskState.PENDING
    retry_count: int = 0
    error_message: str = ""

@dataclass
class QueueState:
    queue_depth: int = 0
    ready_tasks_count: int = 0
    blocked_tasks_count: int = 0
    pending_tasks_count: int = 0
    saturation_status: bool = False
    hwm: int = 8500
    lwm: int = 3000

@dataclass
class WorkerState:
    worker_id: str
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    started_at: Optional[datetime] = None

@dataclass
class SchedulerSession:
    session_id: str
    configuration: SchedulerConfiguration
    start_time: datetime
    lifecycle_state: SchedulerLifecycleState = SchedulerLifecycleState.RUNNING
    metrics: SchedulerMetrics = field(default_factory=SchedulerMetrics)
    health: SchedulerHealth = field(default_factory=SchedulerHealth)
    checkpoint_ref: Optional[SchedulerCheckpoint] = None
