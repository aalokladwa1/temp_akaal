"""
akaalEngine.runtime.models.worker
==================================
Canonical Worker models, WorkerState FSM, WorkerSpec, and WorkerSnapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Sequence


class WorkerState(str, Enum):
    """
    Canonical 6-state Worker Lifecycle.
    """
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    DRAINING = "DRAINING"
    UNHEALTHY = "UNHEALTHY"
    DEREGISTERED = "DEREGISTERED"


@dataclass(frozen=True)
class WorkerCapability:
    """Declared capability of a worker."""
    name: str
    version: str = "1.0.0"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkerSpec:
    """
    Immutable Worker Registration Specification.
    """
    worker_id: str
    node_id: str
    process_id: Optional[int] = None
    capabilities: Sequence[WorkerCapability] = field(default_factory=tuple)
    max_concurrency_slots: int = 10
    total_cpu_cores: float = 4.0
    total_memory_mb: float = 8192.0
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "node_id": self.node_id,
            "process_id": self.process_id,
            "capabilities": [c.name for c in self.capabilities],
            "max_concurrency_slots": self.max_concurrency_slots,
            "total_cpu_cores": self.total_cpu_cores,
            "total_memory_mb": self.total_memory_mb,
            "labels": dict(self.labels),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkerHeartbeat:
    """Worker liveness heartbeat message."""
    worker_id: str
    active_task_count: int = 0
    cpu_percent: float = 0.0
    memory_utilization_pct: float = 0.0
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    fencing_epoch: int = 0


@dataclass(frozen=True)
class WorkerSnapshot:
    """
    Immutable snapshot of worker state at a point in time.
    """
    worker_id: str
    node_id: str
    state: WorkerState
    active_task_count: int
    max_concurrency_slots: int
    fencing_epoch: int
    registered_at: float
    last_heartbeat: float
    capabilities: Sequence[str]
    cpu_percent: float = 0.0
    memory_utilization_pct: float = 0.0

    @property
    def is_available(self) -> bool:
        return self.state == WorkerState.AVAILABLE and self.active_task_count < self.max_concurrency_slots

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "node_id": self.node_id,
            "state": self.state.value,
            "active_task_count": self.active_task_count,
            "max_concurrency_slots": self.max_concurrency_slots,
            "fencing_epoch": self.fencing_epoch,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "capabilities": list(self.capabilities),
            "cpu_percent": self.cpu_percent,
            "memory_utilization_pct": self.memory_utilization_pct,
            "is_available": self.is_available,
        }
