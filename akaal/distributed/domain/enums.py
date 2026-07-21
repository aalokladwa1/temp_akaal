"""
Domain Enums for Enterprise Distributed Runtime.
"""

from enum import Enum, auto


class WorkerStatus(str, Enum):
    """Worker lifecycle states."""
    REGISTERING = "REGISTERING"
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    DRAINING = "DRAINING"
    OFFLINE = "OFFLINE"
    REMOVED = "REMOVED"


class WorkerHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class ClusterState(str, Enum):
    """Cluster State Machine states."""
    INITIALIZING = "INITIALIZING"
    FORMING = "FORMING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"


class ClusterHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class AssignmentState(str, Enum):
    """Task Assignment Lifecycle states."""
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"
    COMPLETED = "COMPLETED"


class FailureType(str, Enum):
    WORKER_FAILURE = "WORKER_FAILURE"
    NODE_FAILURE = "NODE_FAILURE"
    LEADER_FAILURE = "LEADER_FAILURE"
    NETWORK_PARTITION = "NETWORK_PARTITION"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    LEASE_EXPIRATION = "LEASE_EXPIRATION"
