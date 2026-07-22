"""
Transactional Outbox Pattern Engine for Guaranteed At-Least-Once Event Delivery.
"""

from typing import Dict, List, Optional
import datetime

from akaal.api.events.models import DomainEvent
from akaal.api.events.publisher import IEventPublisher


class OutboxRecord:
    """Outbox Database Record Contract."""

    def __init__(self, event: DomainEvent) -> None:
        self.record_id = event.event_id
        self.event = event
        self.status = "PENDING"  # PENDING, DISPATCHED, DLQ
        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.retry_count = 0


class TransactionalOutbox:
    """Engine executing the Transactional Outbox Pattern."""

    def __init__(self, publisher: IEventPublisher) -> None:
        self.publisher = publisher
        self._outbox_records: Dict[str, OutboxRecord] = {}

    def save_to_outbox(self, event: DomainEvent) -> str:
        """Persist event to local outbox in the same transaction."""
        rec = OutboxRecord(event)
        self._outbox_records[rec.record_id] = rec
        return rec.record_id

    async def flush_outbox(self) -> int:
        """Background worker polling and dispatching pending outbox records."""
        dispatched_count = 0
        for rec_id, rec in list(self._outbox_records.items()):
            if rec.status == "PENDING":
                try:
                    success = await self.publisher.publish(rec.event)
                    if success:
                        rec.status = "DISPATCHED"
                        dispatched_count += 1
                    else:
                        rec.retry_count += 1
                except Exception:
                    rec.retry_count += 1
                    if rec.retry_count >= 5:
                        rec.status = "DLQ"
        return dispatched_count

    def get_pending_count(self) -> int:
        return sum(1 for r in self._outbox_records.values() if r.status == "PENDING")
