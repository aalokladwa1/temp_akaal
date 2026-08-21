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
    record_id: str
    idempotency_key: str
    tenant_id: str
    workspace_id: str
    project_id: Optional[str]
    command_name: str
    command_id: str
    payload_fingerprint: str
    result_payload: Mapping[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IdempotencyService:
    @staticmethod
    def compute_record_id(tenant_id: str, workspace_id: str, project_id: Optional[str], command_name: str, idempotency_key: str) -> str:
        return f"{tenant_id}::{workspace_id}::{project_id or ''}::{command_name}::{idempotency_key}"

    def get_idempotent_result(
        self,
        idempotency_key: str,
        tenant_id: str,
        payload_fingerprint: str,
        conn: sqlite3.Connection,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        command_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Fetch previously stored result for tenant/workspace/command scope and idempotency_key."""
        effective_ws = workspace_id or "default-workspace"
        effective_cmd = command_name or "command"
        record_id = self.compute_record_id(tenant_id, effective_ws, project_id, effective_cmd, idempotency_key)

        cur = conn.execute(
            """
            SELECT payload_fingerprint, result_payload, project_id, command_name, tenant_id, workspace_id
            FROM idempotency_records
            WHERE record_id = ?
            """,
            (record_id,),
        )

        row = cur.fetchone()
        if row is None:
            return None

        stored_fingerprint = row["payload_fingerprint"]
        if stored_fingerprint != payload_fingerprint:
            raise IdempotencyConflictError(
                f"Idempotency conflict for key {idempotency_key!r}: stored fingerprint {stored_fingerprint!r} != request fingerprint {payload_fingerprint!r}",
                idempotency_key=idempotency_key,
            )

        if project_id and row["project_id"] and row["project_id"] != project_id:
            raise IdempotencyConflictError(
                f"Idempotency conflict for key {idempotency_key!r}: stored project {row['project_id']!r} != request project {project_id!r}",
                idempotency_key=idempotency_key,
            )

        return json.loads(row["result_payload"])

    def record_idempotent_result(
        self,
        idempotency_key: str,
        tenant_id: str,
        command_id: str,
        payload_fingerprint: str,
        result_payload: Mapping[str, Any],
        conn: sqlite3.Connection,
        workspace_id: str = "default-workspace",
        project_id: Optional[str] = None,
        command_name: str = "command",
    ) -> None:
        """Store exact semantic result for scoped idempotency_key. Rejects concurrent or duplicate overwrites."""
        effective_ws = workspace_id or "default-workspace"
        effective_cmd = command_name or "command"
        record_id = self.compute_record_id(tenant_id, effective_ws, project_id, effective_cmd, idempotency_key)
        try:
            conn.execute(
                """
                INSERT INTO idempotency_records (
                    record_id, idempotency_key, tenant_id, workspace_id, project_id, command_name,
                    command_id, payload_fingerprint, result_payload, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    idempotency_key,
                    tenant_id,
                    effective_ws,
                    project_id,
                    effective_cmd,
                    command_id,
                    payload_fingerprint,
                    json.dumps(result_payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except sqlite3.IntegrityError as e:
            # Check existing record
            cur = conn.execute(
                "SELECT payload_fingerprint, result_payload FROM idempotency_records WHERE record_id = ?",
                (record_id,),
            )
            row = cur.fetchone()
            if row is not None:
                if row["payload_fingerprint"] != payload_fingerprint:
                    raise IdempotencyConflictError(
                        f"Idempotency conflict for key {idempotency_key!r}: stored fingerprint {row['payload_fingerprint']!r} != request fingerprint {payload_fingerprint!r}",
                        idempotency_key=idempotency_key,
                    )
                raise IdempotencyConflictError(
                    f"Idempotent command with key {idempotency_key!r} has already been executed concurrently.",
                    idempotency_key=idempotency_key,
                )
            raise IdempotencyConflictError(
                f"Idempotency integrity error on key {idempotency_key!r}: {e}",
                idempotency_key=idempotency_key,
            )



    def check_and_store(
        self,
        idempotency_key: str,
        command_id: str,
        payload_fingerprint: str,
        result_payload: Mapping[str, Any],
        conn: sqlite3.Connection,
        tenant_id: str = "default-tenant",
        workspace_id: str = "default-workspace",
        project_id: Optional[str] = None,
        command_name: str = "command",
    ) -> Optional[Mapping[str, Any]]:
        cached = self.get_idempotent_result(
            idempotency_key, tenant_id, payload_fingerprint, conn,
            workspace_id=workspace_id, project_id=project_id, command_name=command_name,
        )
        if cached is not None:
            return cached
        if result_payload:
            self.record_idempotent_result(
                idempotency_key, tenant_id, command_id, payload_fingerprint, result_payload, conn,
                workspace_id=workspace_id, project_id=project_id, command_name=command_name,
            )
        return None
