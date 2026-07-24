"""Core Data Models and Enums for Enterprise Replication Platform."""

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class ReplicationMode(str, Enum):
    ACTIVE_ACTIVE = "ACTIVE_ACTIVE"
    ACTIVE_PASSIVE = "ACTIVE_PASSIVE"
    MULTI_MASTER = "MULTI_MASTER"
    REVERSE = "REVERSE"


class ReplicationStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ReplicationOutcome(str, Enum):
    REPLICATED = "REPLICATED"
    SKIPPED = "SKIPPED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    FAILED = "FAILED"


class ConflictResolutionStrategy(str, Enum):
    LAST_WRITE_WINS = "LAST_WRITE_WINS"
    SOURCE_WINS = "SOURCE_WINS"
    TARGET_WINS = "TARGET_WINS"
    MERGE = "MERGE"
    MANUAL_ESCALATE = "MANUAL_ESCALATE"


class ReplicaRole(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    STANDBY = "STANDBY"
    WITNESS = "WITNESS"


@dataclass
class ReplicaNode:
    """Descriptor for a replication node."""

    node_id: str
    region: str
    role: ReplicaRole = ReplicaRole.SECONDARY
    is_active: bool = True
    health_score: float = 100.0
    lag_ms: float = 0.0
    host: str = "localhost"
    port: int = 5432


@dataclass
class ReplicationAction:
    """Individual data replication action."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str = "Cap 1"
    target_table: str = "users"
    source_node_id: str = "node_source"
    target_node_id: str = "node_target"
    mode: ReplicationMode = ReplicationMode.ACTIVE_PASSIVE
    row_count: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplicationPlan:
    """Execution plan containing replication actions."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: List[ReplicationAction] = field(default_factory=list)
    mode: ReplicationMode = ReplicationMode.ACTIVE_PASSIVE
    created_at: float = field(default_factory=time.time)


@dataclass
class ReplicationResult:
    """Result of domain-driven replication execution."""

    domain_name: str
    capabilities_executed: List[str]
    status: ReplicationStatus
    outcome: ReplicationOutcome
    total_actions: int
    successful_actions: int
    failed_actions: int = 0
    confidence_score: float = 100.0
    execution_time_ms: float = 0.0
    action_details: List[Dict[str, Any]] = field(default_factory=list)
