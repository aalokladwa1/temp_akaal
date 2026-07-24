"""Replication Event Models and Event Types."""

import time
from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass, field


class ReplicationEventType(str, Enum):
    REPLICATION_STARTED = "REPLICATION_STARTED"
    REPLICATION_COMPLETED = "REPLICATION_COMPLETED"
    REPLICATION_FAILED = "REPLICATION_FAILED"
    REPLICATION_PAUSED = "REPLICATION_PAUSED"
    REPLICATION_RESUMED = "REPLICATION_RESUMED"
    REPLICATION_ROLLED_BACK = "REPLICATION_ROLLED_BACK"
    REPLICA_PROMOTED = "REPLICA_PROMOTED"
    REPLICA_FAILED = "REPLICA_FAILED"
    FAILOVER_STARTED = "FAILOVER_STARTED"
    FAILOVER_COMPLETED = "FAILOVER_COMPLETED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    TOPOLOGY_UPDATED = "TOPOLOGY_UPDATED"
    HEALTH_UPDATED = "HEALTH_UPDATED"


@dataclass
class ReplicationEvent:
    """Event published during replication lifecycle."""

    event_type: ReplicationEventType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
