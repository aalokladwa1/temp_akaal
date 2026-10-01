"""
akaalEngine.cdc.buffering.backlog
=================================
Memory-bounded CDC Backlog Buffer with Authority #5 Durability spill frame integration.
"""

import json
from collections import deque
import logging
from threading import RLock
import time
from typing import Any, Dict, List, Optional

from akaalEngine.cdc.models.errors import CDCError
from akaalEngine.cdc.models.event import ChangeEvent

logger = logging.getLogger("akaalEngine.cdc.buffering.backlog")


def json_default_serializer(obj: Any) -> Any:
    import decimal
    import datetime
    if isinstance(obj, decimal.Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.hex()
    return str(obj)


class CDCBacklogBuffer:
    """
    Thread-safe, memory-bounded, crash-recoverable CDC Backlog Queue
    physically integrated with Authority #5 Durability (`queue_records` & spill frames).
    """

    def __init__(
        self,
        max_memory_bytes: int = 64 * 1024 * 1024,  # 64MB default
        durability_authority: Optional[Any] = None,
        session_id: str = "default",
    ) -> None:
        self.max_memory_bytes = max_memory_bytes
        self.durability_authority = durability_authority
        self.session_id = session_id
        self._lock = RLock()
        self._queue: deque[ChangeEvent] = deque()
        self._event_msg_map: Dict[str, str] = {}
        self.current_bytes = 0
        self.spilled_count = 0

    def push(self, event: ChangeEvent) -> None:
        """Pushes a ChangeEvent into durable backlog storage and in-memory queue."""
        with self._lock:
            # 1. Durable storage in Authority #5 Durability Queue Store
            if self.durability_authority is not None and hasattr(self.durability_authority, "queue_store"):
                try:
                    payload_bytes = json.dumps(event.to_dict(), default=json_default_serializer).encode("utf-8")
                    msg_id = self.durability_authority.queue_store.store_message(
                        f"cdc_backlog_{self.session_id}", payload_bytes
                    )
                    self._event_msg_map[event.event_id] = msg_id
                except Exception as exc:
                    logger.warning(f"[CDCBacklogBuffer] Durable message persistence warning: {exc}")

            evt_bytes = len(str(event.after_image or "")) + len(str(event.before_image or "")) + 256
            if self.current_bytes + evt_bytes > self.max_memory_bytes:
                if self.durability_authority and hasattr(self.durability_authority, "save_spill_frame"):
                    # Spill over to Authority #5 Durability spill frames
                    spill_payload = json.dumps(event.to_dict(), default=json_default_serializer) if hasattr(event, "to_dict") else str(event.after_image)
                    self.durability_authority.save_spill_frame("cdc_backlog", str(event.event_id), spill_payload)
                    self.spilled_count += 1
                    return

            self._queue.append(event)
            self.current_bytes += evt_bytes

    def append(self, event: ChangeEvent) -> None:
        """Alias for push to support deque-like append interface."""
        self.push(event)

    def pop(self) -> Optional[ChangeEvent]:
        """Pops the next in-memory ChangeEvent."""
        with self._lock:
            if not self._queue:
                return None
            event = self._queue.popleft()
            evt_bytes = len(str(event.after_image or "")) + len(str(event.before_image or "")) + 256
            self.current_bytes = max(0, self.current_bytes - evt_bytes)
            return event

    def ack_event(self, event_id: str) -> bool:
        """
        Acknowledges and durably deletes a processed event from Authority #5 Durability.
        Guarantees that applied and checkpointed events are safely removed.
        """
        with self._lock:
            msg_id = self._event_msg_map.pop(event_id, None)
            if self.durability_authority is not None and hasattr(self.durability_authority, "backend"):
                try:
                    conn = self.durability_authority.backend._get_connection()
                    with self.durability_authority.backend._mutex:
                        conn.execute("BEGIN IMMEDIATE;")
                        if msg_id:
                            conn.execute("DELETE FROM queue_records WHERE message_id = ?;", (msg_id,))
                        else:
                            # Search by matching event_id in payload
                            conn.execute(
                                "DELETE FROM queue_records WHERE queue_name = ? AND payload LIKE ?;",
                                (f"cdc_backlog_{self.session_id}", f'%"event_id": "{event_id}"%')
                            )
                        conn.execute("COMMIT;")
                    return True
                except Exception as exc:
                    logger.warning(f"[CDCBacklogBuffer] Failed to ACK durable message for event '{event_id}': {exc}")
                    return False
            return True

    def recover_pending_events(self, session_id: Optional[str] = None) -> List[ChangeEvent]:
        """
        Recovers unacknowledged pending events from Authority #5 Durability upon process restart.
        Reconstructs in-memory FIFO queue with 100% fidelity.
        """
        with self._lock:
            sess = session_id or self.session_id
            recovered: List[ChangeEvent] = []
            if self.durability_authority is not None and hasattr(self.durability_authority, "backend"):
                conn = self.durability_authority.backend._get_connection()
                q_name = f"cdc_backlog_{sess}"
                cursor = conn.execute(
                    "SELECT message_id, sequence_number, payload FROM queue_records WHERE queue_name = ? ORDER BY sequence_number ASC;",
                    (q_name,)
                )
                rows = cursor.fetchall()
                self._queue.clear()
                self._event_msg_map.clear()
                self.current_bytes = 0
                for row in rows:
                    raw_payload = row["payload"]
                    if isinstance(raw_payload, bytes):
                        raw_payload = raw_payload.decode("utf-8")
                    evt_dict = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                    evt = ChangeEvent.from_dict(evt_dict)
                    recovered.append(evt)
                    self._queue.append(evt)
                    self._event_msg_map[evt.event_id] = row["message_id"]
                    evt_bytes = len(str(evt.after_image or "")) + len(str(evt.before_image or "")) + 256
                    self.current_bytes += evt_bytes
            logger.info(f"[CDCBacklogBuffer] Recovered {len(recovered)} unacknowledged events from durable store for session '{sess}'.")
            return recovered

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
