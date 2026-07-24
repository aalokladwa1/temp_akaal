"""Distributed task queue, leases, and heartbeat for healing cluster."""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class HealingTask:
    task_id: str
    capability_id: str
    domain_name: str
    payload: Dict[str, Any] = field(default_factory=dict)


class DistributedHealingTaskQueue:
    def __init__(self):
        self._queue = asyncio.Queue()

    async def enqueue(self, task: HealingTask) -> None:
        await self._queue.put(task)

    async def dequeue(self, timeout: float = 1.0) -> Optional[HealingTask]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def size(self) -> int:
        return self._queue.qsize()


class HealingTaskLeaseManager:
    def __init__(self, default_ttl_seconds: int = 30):
        self.ttl = default_ttl_seconds
        self._leases: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, task_id: str, worker_id: str) -> bool:
        with self._lock:
            if task_id in self._leases:
                w, exp = self._leases[task_id]
                if w != worker_id and time.time() < exp:
                    return False
            self._leases[task_id] = (worker_id, time.time() + self.ttl)
            return True

    def release_lease(self, task_id: str, worker_id: str) -> None:
        with self._lock:
            if task_id in self._leases and self._leases[task_id][0] == worker_id:
                del self._leases[task_id]


class HealingHeartbeatMonitor:
    def __init__(self, timeout_seconds: int = 15):
        self.timeout = timeout_seconds
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.RLock()

    def record_heartbeat(self, worker_id: str) -> None:
        with self._lock:
            self._heartbeats[worker_id] = time.time()
