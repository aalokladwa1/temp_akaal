"""
WorkerSelector module for ClusterScheduler.
Matches worker capabilities, labels, version compatibility, and resource requirements.
"""

from typing import List, Optional
from threading import RLock

from akaal.distributed.domain.models import Worker, Task
from akaal.distributed.worker.discovery import DiscoveryService


class WorkerSelector:
    """
    WorkerSelector delegates candidate discovery and matching to DiscoveryService.
    """

    def __init__(self, discovery_service: DiscoveryService) -> None:
        self._lock = RLock()
        self._discovery = discovery_service

    def select_candidates(self, task: Task) -> List[Worker]:
        """Find all eligible candidate workers for the task."""
        with self._lock:
            return self._discovery.discover_eligible_workers(
                required_capabilities=task.required_capabilities,
                labels=task.labels,
                min_version=task.min_worker_version,
                only_available=True,
            )
