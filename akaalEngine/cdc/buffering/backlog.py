"""
akaalEngine.cdc.buffering.backlog
=================================
Memory-bounded CDC Backlog Buffer with Authority #5 Durability spill frame integration.
"""

from collections import deque
import logging
from threading import RLock
import time
from typing import Any, Dict, List, Optional

from akaalEngine.cdc.models.errors import CDCError
from akaalEngine.cdc.models.event import ChangeEvent

logger = logging.getLogger("akaalEngine.cdc.buffering.backlog")


class CDCBacklogBuffer:
    """Thread-safe CDC Backlog Queue with memory watermarks and Authority #5 Durability spill overflow."""

    def __init__(
        self,
        max_memory_bytes: int = 64 * 1024 * 1024,  # 64MB default
        durability_authority: Optional[Any] = None,
    ) -> None:
        self.max_memory_bytes = max_memory_bytes
        self.durability_authority = durability_authority
        self._lock = RLock()
        self._queue: deque[ChangeEvent] = deque()
        self.current_bytes = 0
        self.spilled_count = 0

    def push(self, event: ChangeEvent) -> None:
        with self._lock:
            evt_bytes = len(str(event.after_image or "")) + len(str(event.before_image or "")) + 256
            if self.current_bytes + evt_bytes > self.max_memory_bytes:
                if self.durability_authority and hasattr(self.durability_authority, "save_spill_frame"):
                    # Spill over to Authority #5 Durability spill frames
                    self.durability_authority.save_spill_frame("cdc_backlog", str(event.event_id), str(event.after_image))
                    self.spilled_count += 1
                    return

            self._queue.append(event)
            self.current_bytes += evt_bytes

    def pop(self) -> Optional[ChangeEvent]:
        with self._lock:
            if not self._queue:
                return None
            event = self._queue.popleft()
            evt_bytes = len(str(event.after_image or "")) + len(str(event.before_image or "")) + 256
            self.current_bytes = max(0, self.current_bytes - evt_bytes)
            return event

    def drain_backlog(self, timeout_sec: float = 1.0) -> bool:
        """
        Attempts to drain all backlog events within timeout_sec.
        Fails closed with CDCError if backlog remains non-empty when deadline expires.
        """
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            with self._lock:
                if not self._queue:
                    return True
            time.sleep(0.005)

        with self._lock:
            if self._queue:
                raise CDCError(f"Graceful drain timed out: {len(self._queue)} backlog events remain undrained after {timeout_sec}s timeout!")
        return True

    def get_backlog_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "backlog_events": len(self._queue),
                "backlog_bytes": self.current_bytes,
                "spilled_count": self.spilled_count,
            }
