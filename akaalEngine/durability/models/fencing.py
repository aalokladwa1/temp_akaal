"""
Fencing and Lease Models for Authority #5 — Durability.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FencingToken:
    """Immutable fencing token issued to a worker/process."""
    resource_id: str
    worker_id: str
    fencing_epoch: int
    issued_at: str
    signature: str


@dataclass(frozen=True)
class LeaseEpoch:
    """Current generation tracking record for a resource."""
    resource_id: str
    current_epoch: int
    last_worker_id: str
    updated_at: str


# DUR-019: Runtime Fencing Seam
@dataclass(frozen=True)
class RuntimeFencingSeam:
    """Task lease & worker recovery storage model for Runtime."""
    task_id: str
    assigned_worker_id: str
    fencing_token: FencingToken
    heartbeat_deadline: str
    status: str = "ASSIGNED"
