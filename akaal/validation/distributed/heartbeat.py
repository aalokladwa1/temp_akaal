"""HeartbeatMonitor: Worker node heartbeat and failure detection."""

import time
import threading
from typing import Dict, List


class HeartbeatMonitor:
    """Monitors worker node heartbeats and detects dead worker nodes."""

    def __init__(self, timeout_seconds: int = 15):
        self.timeout = timeout_seconds
        # WorkerID -> LastHeartbeatTimestamp
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.RLock()

    def record_heartbeat(self, worker_id: str) -> None:
        """Record heartbeat pulse from worker node."""
        with self._lock:
            self._heartbeats[worker_id] = time.time()

    def get_dead_workers(self) -> List[str]:
        """Return list of worker IDs whose heartbeat timed out."""
        now = time.time()
        with self._lock:
            dead = [w_id for w_id, last_seen in self._heartbeats.items() if now - last_seen > self.timeout]
            for w_id in dead:
                del self._heartbeats[w_id]
            return dead

    def get_active_workers(self) -> List[str]:
        """Return list of active worker IDs."""
        now = time.time()
        with self._lock:
            return [w_id for w_id, last_seen in self._heartbeats.items() if now - last_seen <= self.timeout]
