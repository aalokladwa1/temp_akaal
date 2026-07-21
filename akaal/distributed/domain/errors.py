"""
Distributed Runtime Exception Hierarchy.
Avoids primitive or generic exception handling across distributed components.
"""

from typing import Optional, Any


class DistributedRuntimeError(Exception):
    """Base exception class for all distributed runtime errors."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainValidationError(DistributedRuntimeError):
    """Raised when domain model invariant validation fails on construction."""
    pass


class WorkerUnavailableError(DistributedRuntimeError):
    """Raised when no suitable or healthy worker is available."""
    pass


class SchedulerError(DistributedRuntimeError):
    """Raised when task scheduling fails."""
    pass


class LeaderElectionError(DistributedRuntimeError):
    """Raised during election or leadership split-brain scenarios."""
    pass


class DiscoveryError(DistributedRuntimeError):
    """Raised when worker registration or discovery fails."""
    pass


class CoordinationError(DistributedRuntimeError):
    """Raised during distributed coordination or lock contention failures."""
    pass


class LeaseExpiredError(DistributedRuntimeError):
    """Raised when accessing or renewing an expired task lease."""
    pass


class MembershipError(DistributedRuntimeError):
    """Raised when cluster membership or quorum consistency fails."""
    pass


class ClusterStateError(DistributedRuntimeError):
    """Raised on illegal cluster state machine transitions."""
    pass


class ResourceLimitError(DistributedRuntimeError):
    """Raised when worker or node resource capacity is exceeded."""
    pass


class TaskDistributionError(DistributedRuntimeError):
    """Raised during task queueing, assignment, or distribution failures."""
    pass
