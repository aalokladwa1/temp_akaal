"""
AKAAL Enterprise Platform — Versioned DTO Contracts
====================================================
Backward-compatible, versioned contract models for migration artifacts, events, and snapshots.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass(frozen=True)
class VersionedContract:
    contract_version: str = "v2.0"
    created_at_utc: float = field(default_factory=time.time)


@dataclass(frozen=True)
class MigrationPlanContract(VersionedContract):
    migration_id: str = "mig-default"
    project_id: str = "proj-default"
    source_engine: str = "ORACLE"
    target_engine: str = "POSTGRESQL"
    execution_plan: str = "Topological DAG Stream Partitioning"
    worker_allocation: int = 4
    estimated_duration: str = "< 1 Min"
    estimated_throughput: str = "45.0 MB/s"


@dataclass(frozen=True)
class CheckpointContract(VersionedContract):
    checkpoint_id: str = "chk-default"
    migration_id: str = "mig-default"
    sequence_id: int = 1
    lsn_position: str = "0/1A2B3C4"
    completed_steps: List[str] = field(default_factory=list)
    rows_migrated: int = 0
    checksum_hash: str = ""


@dataclass(frozen=True)
class RuntimeSnapshotContract(VersionedContract):
    migration_id: str = "mig-default"
    runtime_state: str = "active"
    stage: str = "data_migration"
    rows_migrated: int = 5
    rows_validated: int = 5
    throughput_mbps: Optional[float] = None
    active_workers: int = 4
    health_status: str = "HEALTHY"


@dataclass(frozen=True)
class RuntimeEventContract(VersionedContract):
    event_id: str = "evt-default"
    sequence_id: int = 1
    topic: str = "migration.event"
    migration_id: str = "mig-default"
    payload: Dict[str, Any] = field(default_factory=dict)
