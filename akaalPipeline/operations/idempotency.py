"""akaalPipeline.operations.idempotency
======================================
Durable idempotency service backed by relational SQLite tables.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from akaalPipeline.contracts.errors import IdempotencyConflictError


@dataclass(frozen=True)
class IdempotencyRecord:
    idempotency_key: str
    command_id: str
    payload_fingerprint: str
    result_payload: Mapping[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IdempotencyService:
    def check_and_store(
        self,
        idempotency_key: str,
        command_id: str,
        payload_fingerprint: str,
        result_payload: Mapping[str, Any],
        conn: sqlite3.Connection,
    ) -> Optional[Mapping[str, Any]]:
        """Check if idempotency_key exists.
        If exists and payload_fingerprint matches -> return stored result_payload.
        If exists and payload_fingerprint differs -> raise IdempotencyConflictError.
        If not exists -> store and return None.
        """
        cur = conn.execute(
            "SELECT payload_fingerprint, result_payload FROM idempotency_records WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        row = cur.fetchone()
        if row is not None:
            stored_fingerprint = row["payload_fingerprint"]
            if stored_fingerprint != payload_fingerprint:
                raise IdempotencyConflictError(
                    f"Idempotency conflict for key {idempotency_key!r}: stored fingerprint {stored_fingerprint!r} != request fingerprint {payload_fingerprint!r}",
                    idempotency_key=idempotency_key,
                )
            return json.loads(row["result_payload"])

        conn.execute(
            """
            INSERT INTO idempotency_records (idempotency_key, command_id, payload_fingerprint, result_payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                command_id,
                payload_fingerprint,
                json.dumps(result_payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return None
