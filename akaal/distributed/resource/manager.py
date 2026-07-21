"""
ResourceManager module for Distributed Runtime (Platform 2).
Manages CPU, Memory, Concurrency, Disk I/O, Network, and CustomResource allocations,
reservations, and releases using Clock.
"""

from typing import Optional, Dict, Any, List
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import ReservationId, WorkerId
from akaal.distributed.domain.models import ResourceReservation, ResourceSnapshot, CustomResource
from akaal.distributed.domain.errors import ResourceLimitError
from akaal.distributed.clock.clock import Clock, SystemClock

logger = logging.getLogger("nexusforge.distributed.resource")


class ResourceManager:
    """
    Thread-safe ResourceManager for tracking capacity, reservations, and resource releases.
    """

    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._lock = RLock()
        self._clock = clock or SystemClock()
        self._reservations: Dict[str, ResourceReservation] = {}

    def create_reservation(
        self,
        worker_id: WorkerId,
        cpu_cores: float,
        memory_mb: float,
        concurrency: int = 1,
        ttl_seconds: float = 60.0,
    ) -> ResourceReservation:
        """Create a resource reservation."""
        with self._lock:
            now = self._clock.now_timestamp()
            resv = ResourceReservation(
                reservation_id=ReservationId.generate(),
                worker_id=worker_id,
                cpu_cores=cpu_cores,
                memory_mb=memory_mb,
                concurrency=concurrency,
                created_at=now,
                expires_at=now + ttl_seconds,
            )
            self._reservations[str(resv.reservation_id)] = resv
            return resv

    def release_reservation(self, reservation_id: ReservationId) -> None:
        """Release a resource reservation."""
        with self._lock:
            self._reservations.pop(str(reservation_id), None)

    def evict_expired_reservations(self) -> List[ResourceReservation]:
        """Evict expired resource reservations based on Clock."""
        with self._lock:
            now = self._clock.now_timestamp()
            expired: List[ResourceReservation] = []

            for r_id, resv in list(self._reservations.items()):
                if resv.expires_at < now:
                    expired.append(resv)
                    self._reservations.pop(r_id, None)

            return expired
