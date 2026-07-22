"""
CDC Failover package initialization.
"""

from akaal.cdc.failover.coordinator import CDCFailoverCoordinator, WorkerFailoverManager

__all__ = ["CDCFailoverCoordinator", "WorkerFailoverManager"]
