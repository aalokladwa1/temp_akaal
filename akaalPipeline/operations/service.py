"""akaalPipeline.operations.service
==================================
Durable operation journal service.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from akaalPipeline.contracts.enums import OperationStatus
from akaalPipeline.operations.models import OperationRecord


class OperationService:
    def create_operation(self, record: OperationRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO operation_journal (
                operation_id, command_id, idempotency_key, status, actor,
                payload_fingerprint, result_payload, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.operation_id,
                record.command_id,
                record.idempotency_key,
                record.status.value,
                json.dumps(record.actor.to_dict()),
                record.payload_fingerprint,
                json.dumps(record.result_payload) if record.result_payload is not None else None,
                json.dumps(record.error) if record.error is not None else None,
                record.created_at,
                record.updated_at,
            ),
        )

    def update_status(
        self,
        operation_id: str,
        status: OperationStatus,
        conn: sqlite3.Connection,
        result_payload: Optional[Mapping[str, Any]] = None,
        error: Optional[Mapping[str, Any]] = None,
    ) -> None:
        conn.execute(
            """
            UPDATE operation_journal SET
                status = ?, result_payload = ?, error = ?, updated_at = ?
            WHERE operation_id = ?
            """,
            (
                status.value,
                json.dumps(result_payload) if result_payload is not None else None,
                json.dumps(error) if error is not None else None,
                datetime.now(timezone.utc).isoformat(),
                operation_id,
            ),
        )

    def get_by_id(self, operation_id: str, conn: sqlite3.Connection) -> Optional[OperationRecord]:
        cur = conn.execute("SELECT * FROM operation_journal WHERE operation_id = ?", (operation_id,))
        row = cur.fetchone()
        if row is None:
            return None
        data = {
            "operation_id": row["operation_id"],
            "command_id": row["command_id"],
            "idempotency_key": row["idempotency_key"],
            "status": row["status"],
            "actor": json.loads(row["actor"]),
            "payload_fingerprint": row["payload_fingerprint"],
            "result_payload": json.loads(row["result_payload"]) if row["result_payload"] else None,
            "error": json.loads(row["error"]) if row["error"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        return OperationRecord.from_dict(data)
