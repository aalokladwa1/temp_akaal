"""DistributedTaskQueue: Asynchronous cluster-safe task queue."""

import asyncio
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DistributedTask:
    task_id: str
    capability_id: str
    domain_name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 3


class DistributedTaskQueue:
    """Cluster task queue managing pending validation chunks."""

    def __init__(self):
        self._queue = asyncio.Queue()

    async def enqueue(self, task: DistributedTask) -> None:
        """Enqueue task for processing."""
        await self._queue.put(task)

    async def dequeue(self, timeout: float = 1.0) -> Optional[DistributedTask]:
        """Dequeue task with timeout."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def size(self) -> int:
        """Return pending queue size."""
        return self._queue.qsize()
