"""akaalPipeline.events.outbox
=============================
Real transactional outbox table service.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from akaalPipeline.events.schemas import DomainEvent


@dataclass(frozen=True)
class OutboxEvent:
    event_id: str
    aggregate_id: str
    event_type: str
    payload: dict
    status: str  # 'PENDING', 'PUBLISHED'
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutboxService:
    def stage_event(self, event: DomainEvent, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO outbox_events (event_id, aggregate_id, event_type, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.aggregate_id,
                event.event_type,
                json.dumps(dict(event.payload)),
                "PENDING",
                event.timestamp,
            ),
        )

    def fetch_pending(self, conn: sqlite3.Connection, limit: int = 50) -> List[OutboxEvent]:
        cur = conn.execute(
            "SELECT * FROM outbox_events WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            OutboxEvent(
                event_id=row["event_id"],
                aggregate_id=row["aggregate_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload"]),
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def mark_published(self, event_id: str, conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE outbox_events SET status = 'PUBLISHED' WHERE event_id = ?", (event_id,))
