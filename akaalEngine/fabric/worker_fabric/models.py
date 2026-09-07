"""
akaalEngine.fabric.worker_fabric.models
==========================================
P7B.22 -- Elastic Worker Fabric: WorkerNode model.

ABSOLUTE LAW:

    WORKER HEARTBEAT != TRUSTED OWNERSHIP.
    WORKER REGISTRATION != TRUSTED WORKER.
    WORKER CAPACITY CLAIM != TRUSTED CAPACITY.
    A SINGLE UNTRUSTED WORKER CANNOT MANUFACTURE GLOBAL SCALING TRUTH.

A `WorkerNode`'s `capabilities`/`capacity` fields are self-reported claims, exactly like
`ExecutionSite.capabilities` (P7B.5) -- this module never treats registration or
heartbeat alone as proof of trustworthiness. Whether a worker's claims are trusted enough
to actually receive assignments remains
`akaalEngine.fabric.placement.capability`/`policy` territory (composed with
`akaalEngine.fabric.execution_site.SiteRegistry`'s existing site trust ladder) -- this
module only tracks WHAT was claimed and WHEN, plus fencing-epoch replacement safety.

Fencing reuses the exact same epoch-monotonicity discipline as
`akaalEngine.fabric.execution_site.models.SiteAssignment`/`SiteRegistry` (P7B.5/9) --
never a second, independently-invented fencing scheme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Optional
from types import MappingProxyType
from typing import Mapping


class WorkerState(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    DRAINING = "DRAINING"
    UNHEALTHY = "UNHEALTHY"
    REVOKED = "REVOKED"
    STALE = "STALE"


_ACTIVE_STATES = frozenset({WorkerState.IDLE, WorkerState.BUSY, WorkerState.DRAINING})


class WorkerValidationError(ValueError):
    pass


@dataclass(frozen=True)
class WorkerCapacity:
    """Self-reported capacity claim, provenance-tracked exactly like
    akaalEngine.fabric.placement.capability.CapacityOffer (the two are intentionally
    structurally similar -- a worker's registered/heartbeat capacity IS the source a
    production caller would read to build a CapacityOffer at placement-evaluation time;
    this module does not duplicate that evaluation logic, only the data shape)."""
    cpu_cores: Optional[float] = None
    memory_mb: Optional[int] = None
    disk_mb: Optional[int] = None
    concurrency_slots: Optional[int] = None
    throughput_mbps: Optional[float] = None
    provenance: str = ""

    def __post_init__(self) -> None:
        for name in ("cpu_cores", "memory_mb", "disk_mb", "concurrency_slots", "throughput_mbps"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise WorkerValidationError(f"WorkerCapacity.{name} must be >= 0 if supplied; got {value!r}.")


@dataclass(frozen=True)
class WorkerNode:
    worker_id: str
    site_id: str
    tenant_id: str
    runtime_version: str
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    capability_provenance: str = "UNKNOWN"
    capacity: Optional[WorkerCapacity] = None
    state: WorkerState = WorkerState.IDLE
    fencing_epoch: int = 1
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    labels: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.worker_id or not self.worker_id.strip():
            raise WorkerValidationError("WorkerNode.worker_id must be non-empty.")
        if not self.site_id or not self.site_id.strip():
            raise WorkerValidationError("WorkerNode.site_id must be non-empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise WorkerValidationError("WorkerNode.tenant_id must be non-empty.")
        if not self.runtime_version or not self.runtime_version.strip():
            raise WorkerValidationError("WorkerNode.runtime_version must be non-empty.")
        if self.fencing_epoch < 1:
            raise WorkerValidationError("WorkerNode.fencing_epoch must be >= 1.")
        if not isinstance(self.capabilities, frozenset):
            object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        if not isinstance(self.labels, MappingProxyType):
            object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))

    def is_active(self) -> bool:
        return self.state in _ACTIVE_STATES

    def is_schedulable(self) -> bool:
        """Purely informational -- NEVER an authorization grant. Mirrors
        ExecutionSite.is_execution_authorized()'s "informational readiness, not a grant"
        discipline exactly."""
        return self.state == WorkerState.IDLE

    def seconds_since_heartbeat(self, now: Optional[datetime] = None) -> float:
        current = now or datetime.now(timezone.utc)
        last = datetime.fromisoformat(self.last_heartbeat_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (current - last).total_seconds()
