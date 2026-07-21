"""
DiscoveryService module for Distributed Runtime (Platform 2).
Provides capability, label, health, and version compatibility worker filtering.
"""

from typing import List, Optional, Dict, Any
from threading import RLock

from akaal.distributed.domain.identifiers import WorkerId
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth
from akaal.distributed.domain.models import Worker, Task
from akaal.distributed.repository.interfaces import WorkerRepository


class DiscoveryService:
    """
    Storage-agnostic DiscoveryService for discovering and filtering eligible workers.
    """

    def __init__(self, repository: WorkerRepository) -> None:
        self._lock = RLock()
        self._repository = repository

    def discover_eligible_workers(
        self,
        required_capabilities: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        min_version: str = "1.0.0",
        only_available: bool = True,
    ) -> List[Worker]:
        """Filter workers matching capabilities, labels, health, and minimum version."""
        with self._lock:
            candidates = self._repository.list_workers(health=WorkerHealth.HEALTHY)
            eligible: List[Worker] = []

            for w in candidates:
                if only_available and w.status not in (WorkerStatus.AVAILABLE, WorkerStatus.BUSY):
                    continue

                if w.current_load >= w.capacity:
                    continue

                # Capability matching
                if required_capabilities:
                    cap_names = {c.name for c in w.capabilities}
                    if not set(required_capabilities).issubset(cap_names):
                        continue

                # Label matching
                if labels:
                    match = True
                    for l_key, l_val in labels.items():
                        if w.labels.get(l_key) != l_val:
                            match = False
                            break
                    if not match:
                        continue

                # Version check (simplified string comparison)
                if w.worker_version < min_version:
                    continue

                eligible.append(w)

            return eligible
