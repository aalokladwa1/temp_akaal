"""RepairPriorityQueue & QueueManager for SLA-aware priority repair queue."""

import heapq
import threading
from typing import Any, List, Optional
from dataclasses import dataclass, field


@dataclass(order=True)
class PrioritizedRepairItem:
    priority_score: float
    item_id: str = field(compare=False)
    payload: Any = field(compare=False)


class RepairPriorityQueue:
    """Thread-safe priority queue for repair jobs."""

    def __init__(self):
        self._heap: List[PrioritizedRepairItem] = []
        self._lock = threading.RLock()

    def push(self, item_id: str, payload: Any, priority_score: float) -> None:
        """Push item with priority score (higher priority score pops first)."""
        with self._lock:
            # Reverse priority_score for max-heap behavior using heapq min-heap
            heapq.heappush(self._heap, PrioritizedRepairItem(priority_score=-priority_score, item_id=item_id, payload=payload))

    def pop(self) -> Optional[Any]:
        """Pop highest priority repair item."""
        with self._lock:
            if not self._heap:
                return None
            item = heapq.heappop(self._heap)
            return item.payload

    def size(self) -> int:
        with self._lock:
            return len(self._heap)


class QueueManager:
    """Manages active repair queue lifecycle."""

    def __init__(self):
        self.queue = RepairPriorityQueue()
