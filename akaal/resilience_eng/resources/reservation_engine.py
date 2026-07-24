"""Resource Reservation Engine, Allocator, and Quotas."""

import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ResourceReservation:
    reservation_id: str = field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    experiment_id: str = "exp_001"
    cpu_cores: int = 2
    memory_mb: int = 2048
    allocated_at: float = field(default_factory=time.time)


class QuotaEnforcementManager:
    """Enforces quota limits for CPU, Memory, and Workers."""

    def __init__(self, max_cores: int = 16, max_memory_mb: int = 16384):
        self.max_cores = max_cores
        self.max_memory_mb = max_memory_mb

    def check_quota(self, requested_cores: int, requested_memory_mb: int) -> bool:
        return requested_cores <= self.max_cores and requested_memory_mb <= self.max_memory_mb


class ResourceAllocator:
    """Allocates temporary resources for isolated experiment execution."""

    def allocate(self, reservation: ResourceReservation) -> bool:
        return True


class ResourceReservationEngine:
    """Thread-safe engine managing resource reservations and windows."""

    def __init__(self):
        self.quota_mgr = QuotaEnforcementManager()
        self.allocator = ResourceAllocator()
        self._reservations: Dict[str, ResourceReservation] = {}
        self._lock = threading.RLock()

    def reserve_resources(self, experiment_id: str, cores: int = 2, memory_mb: int = 2048) -> Optional[ResourceReservation]:
        with self._lock:
            if not self.quota_mgr.check_quota(cores, memory_mb):
                return None
            res = ResourceReservation(experiment_id=experiment_id, cpu_cores=cores, memory_mb=memory_mb)
            self.allocator.allocate(res)
            self._reservations[experiment_id] = res
            return res

    def release_reservation(self, experiment_id: str) -> None:
        with self._lock:
            if experiment_id in self._reservations:
                del self._reservations[experiment_id]
