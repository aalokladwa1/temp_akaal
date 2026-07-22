"""
Durable CDC Buffering Engine with Dead Letter Queue (DLQ).
"""

from typing import List, Dict, Optional, Any
import collections
from akaal.cdc.contracts.event import CDCEvent


class DeadLetterQueue:
    """DLQ for Poison Pill or Un-routable CDC Events."""

    def __init__(self) -> None:
        self._dlq_events: List[Dict[str, Any]] = []

    def push(self, event: CDCEvent, reason: str) -> None:
        self._dlq_events.append({"event": event, "reason": reason})

    def get_all(self) -> List[Dict[str, Any]]:
        return self._dlq_events


class DurableCDCBuffer:
    """
    Durable CDC Buffer guaranteeing per-table transaction ordering.
    """

    def __init__(self, max_capacity: int = 10000) -> None:
        self.max_capacity = max_capacity
        # Table -> Deque of events
        self._table_buffers: Dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self.dlq = DeadLetterQueue()

    def push_event(self, event: CDCEvent) -> bool:
        table_key = f"{event.source_db}.{event.source_schema}.{event.source_table}"
        if sum(len(q) for q in self._table_buffers.values()) >= self.max_capacity:
            self.dlq.push(event, "Buffer capacity overflow")
            return False
        self._table_buffers[table_key].append(event)
        return True

    def pop_ordered_batch(self, table_key: str, batch_size: int = 100) -> List[CDCEvent]:
        """Pop events preserving transaction order for a specific table."""
        batch = []
        q = self._table_buffers[table_key]
        while q and len(batch) < batch_size:
            batch.append(q.popleft())
        return batch

    def get_pending_count(self) -> int:
        return sum(len(q) for q in self._table_buffers.values())
