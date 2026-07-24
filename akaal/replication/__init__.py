"""AKAAL Phase 11 Platform 3: Enterprise Replication Platform."""

from akaal.replication.facade.platform3 import EnterpriseReplicationPlatformV3
from akaal.replication.core.config import ReplicationConfig, ReplicationProfile, FailoverMode
from akaal.replication.core.context import ReplicationContext
from akaal.replication.core.models import (
    ReplicationPlan,
    ReplicationResult,
    ReplicationStatus,
    ReplicationOutcome,
    ReplicationMode,
    ConflictResolutionStrategy,
    ReplicaNode,
    ReplicaRole,
)

__all__ = [
    "EnterpriseReplicationPlatformV3",
    "ReplicationConfig",
    "ReplicationProfile",
    "FailoverMode",
    "ReplicationContext",
    "ReplicationPlan",
    "ReplicationResult",
    "ReplicationStatus",
    "ReplicationOutcome",
    "ReplicationMode",
    "ConflictResolutionStrategy",
    "ReplicaNode",
    "ReplicaRole",
]
