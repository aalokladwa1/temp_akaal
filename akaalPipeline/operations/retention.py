"""akaalPipeline.operations.retention
==================================
Operational retention policy enforcement, multi-class protection engine, non-destructive preview, and bounded batch pruning.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from akaalPipeline.contracts.enums import MigrationLifecycleState, OperationStatus, RetentionProtectionClass
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.security.context import PipelineActorContext


@dataclass
class RetentionPolicy:
    cutoff_time: str
    tenant_id: str = "default-tenant"
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    data_classes: List[str] = field(default_factory=lambda: [
        "operation_journal",
        "idempotency_records",
        "lifecycle_history",
        "outbox_events",
        "checkpoints",
        "immutable_artifacts",
        "audit_trail",
        "schedule_occurrences",
    ])
    max_batch_size: int = 500


@dataclass
class RetentionPreviewResult:
    preview_id: str
    cutoff_time: str
    tenant_id: str
    data_classes: List[str]
    considered_count: int
    eligible_count: int
    protected_count: int
    protection_breakdown: Dict[str, int]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "preview_id": self.preview_id,
            "cutoff_time": self.cutoff_time,
            "tenant_id": self.tenant_id,
            "data_classes": self.data_classes,
            "considered_count": self.considered_count,
            "eligible_count": self.eligible_count,
            "protected_count": self.protected_count,
            "protection_breakdown": self.protection_breakdown,
            "generated_at": self.generated_at,
        }


@dataclass
class RetentionExecutionResult:
    retention_op_id: str
    tenant_id: str
    status: str
    cutoff_time: str
    data_classes: List[str]
    considered_count: int
    eligible_count: int
    deleted_count: int
    protected_count: int
    failed_count: int
    protection_breakdown: Dict[str, int]
    error_details: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "retention_op_id": self.retention_op_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "cutoff_time": self.cutoff_time,
            "data_classes": self.data_classes,
            "considered_count": self.considered_count,
            "eligible_count": self.eligible_count,
            "deleted_count": self.deleted_count,
            "protected_count": self.protected_count,
            "failed_count": self.failed_count,
            "protection_breakdown": self.protection_breakdown,
            "error_details": self.error_details,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class OperationalRetentionService:
    """Enterprise operational retention authority protecting Evidence #12, active executions, recovery state, and audit trails."""

    ACTIVE_MIGRATION_STATES = {
        MigrationLifecycleState.INITIALIZED.value,
        MigrationLifecycleState.ACTIVE.value,
        MigrationLifecycleState.PAUSING.value,
        MigrationLifecycleState.PAUSED.value,
        MigrationLifecycleState.CONFIGURING.value,
        MigrationLifecycleState.GOVERNANCE_PENDING.value,
        MigrationLifecycleState.AUTHORIZED.value,
        MigrationLifecycleState.PLANNED.value,
    }

    def preview(
        self,
        policy: RetentionPolicy,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
    ) -> RetentionPreviewResult:
        """Non-destructively evaluate retention candidates against all protection classes. Zero database mutation."""
        analysis = self._analyze_candidates(policy, conn, actor=actor)

        preview_id = f"prev-ret-{uuid.uuid4().hex[:12]}"
        return RetentionPreviewResult(
            preview_id=preview_id,
            cutoff_time=policy.cutoff_time,
            tenant_id=policy.tenant_id,
            data_classes=policy.data_classes,
            considered_count=analysis["total_considered"],
            eligible_count=analysis["total_eligible"],
            protected_count=analysis["total_protected"],
            protection_breakdown=analysis["protection_breakdown"],
        )

    def execute(
        self,
        policy: RetentionPolicy,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        batch_size: int = 500,
        max_records: Optional[int] = None,
    ) -> RetentionExecutionResult:
        """Re-evaluates protection predicates, performs bounded batch pruning, and journals the operation."""
        now_iso = datetime.now(timezone.utc).isoformat()
        retention_op_id = f"ret-op-{uuid.uuid4().hex[:12]}"
        initiator = actor.actor_id if actor else "system-retention"

        # Re-evaluate live analysis to protect against state changes between preview and execution
        analysis = self._analyze_candidates(policy, conn, actor=actor)

        deleted_total = 0
        failed_total = 0
        status = "COMPLETED"
        err_msg = None

        # Execute bounded deletions for eligible IDs per data class
        for dclass, eligible_ids in analysis["eligible_by_class"].items():
            if not eligible_ids:
                continue

            # Bounded batching
            for i in range(0, len(eligible_ids), batch_size):
                if max_records is not None and deleted_total >= max_records:
                    break
                chunk = eligible_ids[i : i + batch_size]
                if max_records is not None and (deleted_total + len(chunk)) > max_records:
                    chunk = chunk[: max_records - deleted_total]
                try:
                    del_count = self._delete_batch(dclass, chunk, policy.tenant_id, conn)
                    deleted_total += del_count
                except Exception as exc:
                    failed_total += len(chunk)
                    status = "PARTIALLY_FAILED"
                    err_msg = f"Error pruning {dclass}: {exc}"

            if max_records is not None and deleted_total >= max_records:
                break

        completed_iso = datetime.now(timezone.utc).isoformat()

        # Journal retention operation
        conn.execute(
            """
            INSERT INTO retention_operations (
                retention_op_id, tenant_id, workspace_id, project_id, initiator_actor_id,
                is_preview, cutoff_time, data_classes, status, considered_count,
                eligible_count, deleted_count, protected_count, failed_count,
                protection_breakdown, error_details, created_at, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                retention_op_id,
                policy.tenant_id,
                policy.workspace_id or "default-workspace",
                policy.project_id,
                initiator,
                0,
                policy.cutoff_time,
                json.dumps(policy.data_classes),
                status,
                analysis["total_considered"],
                analysis["total_eligible"],
                deleted_total,
                analysis["total_protected"],
                failed_total,
                json.dumps(analysis["protection_breakdown"]),
                err_msg,
                now_iso,
                completed_iso,
            ),
        )

        return RetentionExecutionResult(
            retention_op_id=retention_op_id,
            tenant_id=policy.tenant_id,
            status=status,
            cutoff_time=policy.cutoff_time,
            data_classes=policy.data_classes,
            considered_count=analysis["total_considered"],
            eligible_count=analysis["total_eligible"],
            deleted_count=deleted_total,
            protected_count=analysis["total_protected"],
            failed_count=failed_total,
            protection_breakdown=analysis["protection_breakdown"],
            error_details=err_msg,
            started_at=now_iso,
            completed_at=completed_iso,
        )

    def get_operation_by_id(self, retention_op_id: str, conn: sqlite3.Connection) -> Optional[RetentionExecutionResult]:
        cur = conn.execute("SELECT * FROM retention_operations WHERE retention_op_id = ?", (retention_op_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_execution_result(row)

    def list_operations(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[RetentionExecutionResult]:
        cur = conn.execute(
            "SELECT * FROM retention_operations WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
        return [self._row_to_execution_result(r) for r in cur.fetchall()]

    def _analyze_candidates(
        self,
        policy: RetentionPolicy,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
    ) -> Dict[str, Any]:
        """Perform granular candidate discovery and evaluate protection predicates."""
        tenant_id = policy.tenant_id
        cutoff = policy.cutoff_time

        # 1. Discover Active Migration IDs (for Active Reference Protection)
        cur = conn.execute("SELECT migration_id, state FROM migrations WHERE tenant_id = ?", (tenant_id,))
        active_migration_ids: Set[str] = {
            r["migration_id"] for r in cur.fetchall() if r["state"] in self.ACTIVE_MIGRATION_STATES
        }

        # 2. Discover Ambiguous Operations (for Ambiguous Idempotency & Operation Journal Protection)
        cur = conn.execute("SELECT operation_id, idempotency_key, error FROM operation_journal WHERE tenant_id = ? AND status = 'FAILED'", (tenant_id,))
        ambiguous_op_ids: Set[str] = set()
        ambiguous_idem_keys: Set[str] = set()
        for r in cur.fetchall():
            err = r["error"]
            if err:
                try:
                    err_dict = json.loads(err) if isinstance(err, str) else err
                    if err_dict.get("details", {}).get("reconciliation_required") is True or err_dict.get("reconciliation_required") is True:
                        ambiguous_op_ids.add(r["operation_id"])
                        if r["idempotency_key"]:
                            ambiguous_idem_keys.add(r["idempotency_key"])
                except Exception:
                    pass

        protection_breakdown: Dict[str, int] = {
            RetentionProtectionClass.EVIDENCE_PROTECTED.value: 0,
            RetentionProtectionClass.RECOVERY_SENSITIVE.value: 0,
            RetentionProtectionClass.GOVERNANCE_SENSITIVE.value: 0,
            RetentionProtectionClass.ACTIVE_REFERENCE_PROTECTED.value: 0,
            RetentionProtectionClass.IDEMPOTENCY_SAFETY.value: 0,
        }

        eligible_by_class: Dict[str, List[str]] = {}
        total_considered = 0
        total_eligible = 0
        total_protected = 0

        for dclass in policy.data_classes:
            eligible_by_class[dclass] = []

            # -------------------------------------------------------------
            # Class: operation_journal
            # -------------------------------------------------------------
            if dclass == "operation_journal":
                cur = conn.execute(
                    "SELECT operation_id, status, error, created_at FROM operation_journal WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    op_id = r["operation_id"]
                    if op_id in ambiguous_op_ids:
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.ACTIVE_REFERENCE_PROTECTED.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(op_id)

            # -------------------------------------------------------------
            # Class: idempotency_records
            # -------------------------------------------------------------
            elif dclass == "idempotency_records":
                cur = conn.execute(
                    "SELECT record_id, idempotency_key, result_payload, created_at FROM idempotency_records WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    rec_id = r["record_id"]
                    idem_key = r["idempotency_key"]
                    if idem_key in ambiguous_idem_keys:
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.IDEMPOTENCY_SAFETY.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(rec_id)

            # -------------------------------------------------------------
            # Class: lifecycle_history
            # -------------------------------------------------------------
            elif dclass == "lifecycle_history":
                cur = conn.execute(
                    "SELECT history_id, migration_id, timestamp FROM lifecycle_history WHERE tenant_id = ? AND timestamp < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    hid = r["history_id"]
                    mid = r["migration_id"]
                    if mid in active_migration_ids:
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.ACTIVE_REFERENCE_PROTECTED.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(hid)

            # -------------------------------------------------------------
            # Class: outbox_events
            # -------------------------------------------------------------
            elif dclass == "outbox_events":
                cur = conn.execute(
                    "SELECT event_id, aggregate_id, status, created_at FROM outbox_events WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    eid = r["event_id"]
                    agg_id = r["aggregate_id"]
                    status = r["status"]
                    if status == "PENDING" or agg_id in active_migration_ids:
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.ACTIVE_REFERENCE_PROTECTED.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(eid)

            # -------------------------------------------------------------
            # Class: checkpoints
            # -------------------------------------------------------------
            elif dclass == "checkpoints":
                cur = conn.execute(
                    "SELECT checkpoint_id, migration_id, created_at FROM checkpoints WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    cid = r["checkpoint_id"]
                    mid = r["migration_id"]
                    if mid in active_migration_ids:
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.RECOVERY_SENSITIVE.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(cid)

            # -------------------------------------------------------------
            # Class: immutable_artifacts (Evidence #12 Protection)
            # -------------------------------------------------------------
            elif dclass == "immutable_artifacts":
                cur = conn.execute(
                    "SELECT artifact_id, artifact_type, created_at FROM immutable_artifacts WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    # INVARIANT: Evidence #12 and immutable artifacts are ALWAYS protected from generic operational retention!
                    total_protected += 1
                    protection_breakdown[RetentionProtectionClass.EVIDENCE_PROTECTED.value] += 1

            # -------------------------------------------------------------
            # Class: audit_trail (Governance & Compliance Protection)
            # -------------------------------------------------------------
            elif dclass == "audit_trail":
                cur = conn.execute(
                    "SELECT audit_id, created_at FROM audit_trail WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    # INVARIANT: Audit trail records are protected by governance policy
                    total_protected += 1
                    protection_breakdown[RetentionProtectionClass.GOVERNANCE_SENSITIVE.value] += 1

            # -------------------------------------------------------------
            # Class: schedule_occurrences
            # -------------------------------------------------------------
            elif dclass == "schedule_occurrences":
                cur = conn.execute(
                    "SELECT occurrence_id, status, created_at FROM schedule_occurrences WHERE tenant_id = ? AND created_at < ?",
                    (tenant_id, cutoff),
                )
                for r in cur.fetchall():
                    total_considered += 1
                    oid = r["occurrence_id"]
                    ostatus = r["status"]
                    if ostatus in ("PENDING", "CLAIMED", "DISPATCHED"):
                        total_protected += 1
                        protection_breakdown[RetentionProtectionClass.ACTIVE_REFERENCE_PROTECTED.value] += 1
                    else:
                        total_eligible += 1
                        eligible_by_class[dclass].append(oid)

        return {
            "total_considered": total_considered,
            "total_eligible": total_eligible,
            "total_protected": total_protected,
            "protection_breakdown": protection_breakdown,
            "eligible_by_class": eligible_by_class,
        }

    def _delete_batch(
        self,
        dclass: str,
        ids: List[str],
        tenant_id: str,
        conn: sqlite3.Connection,
    ) -> int:
        """Execute atomic deletion of a batch of IDs for a given table with tenant scoping."""
        if not ids:
            return 0

        param_marks = ",".join("?" for _ in ids)
        id_col_map = {
            "operation_journal": ("operation_journal", "operation_id"),
            "idempotency_records": ("idempotency_records", "record_id"),
            "lifecycle_history": ("lifecycle_history", "history_id"),
            "outbox_events": ("outbox_events", "event_id"),
            "checkpoints": ("checkpoints", "checkpoint_id"),
            "schedule_occurrences": ("schedule_occurrences", "occurrence_id"),
        }

        if dclass not in id_col_map:
            return 0

        table_name, col_name = id_col_map[dclass]
        query = f"DELETE FROM {table_name} WHERE tenant_id = ? AND {col_name} IN ({param_marks})"
        params = [tenant_id] + ids
        cur = conn.execute(query, tuple(params))
        return cur.rowcount

    @staticmethod
    def _row_to_execution_result(row: sqlite3.Row) -> RetentionExecutionResult:
        breakdown = json.loads(row["protection_breakdown"]) if row["protection_breakdown"] else {}
        dclasses = json.loads(row["data_classes"]) if row["data_classes"] else []
        return RetentionExecutionResult(
            retention_op_id=row["retention_op_id"],
            tenant_id=row["tenant_id"],
            status=row["status"],
            cutoff_time=row["cutoff_time"],
            data_classes=dclasses,
            considered_count=int(row["considered_count"]),
            eligible_count=int(row["eligible_count"]),
            deleted_count=int(row["deleted_count"]),
            protected_count=int(row["protected_count"]),
            failed_count=int(row["failed_count"]),
            protection_breakdown=breakdown,
            error_details=row["error_details"],
            started_at=row["created_at"],
            completed_at=row["completed_at"],
        )
