"""akaalPipeline.operations.schedules
===================================
Durable schedule lifecycle, recurrence resolution, lease-fenced occurrence claiming, and execution management.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaalPipeline.contracts.enums import (
    MisfirePolicy,
    OccurrenceStatus,
    OverlapPolicy,
    ScheduleLifecycleState,
    ScheduleType,
)
from akaalPipeline.contracts.errors import (
    LeaseConflictError,
    PipelineError,
    PipelineErrorCode,
    UnableToAcquireLeaseError,
)
from akaalPipeline.operations.cron import compute_next_occurrence, validate_cron_expression, validate_timezone
from akaalPipeline.operations.leases import ExecutionLease, LeaseManager
from akaalPipeline.state.lifecycle import ScheduleLifecycleMachine


@dataclass
class ScheduleRecord:
    schedule_id: str
    migration_id: str
    cron_expression: str
    state: ScheduleLifecycleState
    tenant_id: str = "default-tenant"
    workspace_id: str = "default-workspace"
    project_id: Optional[str] = None
    operation_type: str = "migration.start"
    schedule_type: ScheduleType = ScheduleType.RECURRING
    one_shot_time: Optional[str] = None
    timezone: str = "UTC"
    enabled: bool = True
    revision: int = 1
    misfire_policy: MisfirePolicy = MisfirePolicy.SKIP
    overlap_policy: OverlapPolicy = OverlapPolicy.REJECT_OVERLAP
    activation_id: Optional[str] = None
    creator_actor_id: Optional[str] = None
    delegated_roles: Optional[str] = None
    last_occurrence_time: Optional[str] = None
    next_occurrence_time: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "operation_type": self.operation_type,
            "schedule_type": self.schedule_type.value if hasattr(self.schedule_type, "value") else str(self.schedule_type),
            "cron_expression": self.cron_expression,
            "one_shot_time": self.one_shot_time,
            "timezone": self.timezone,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "enabled": bool(self.enabled),
            "revision": self.revision,
            "misfire_policy": self.misfire_policy.value if hasattr(self.misfire_policy, "value") else str(self.misfire_policy),
            "overlap_policy": self.overlap_policy.value if hasattr(self.overlap_policy, "value") else str(self.overlap_policy),
            "activation_id": self.activation_id,
            "creator_actor_id": self.creator_actor_id,
            "delegated_roles": self.delegated_roles,
            "last_occurrence_time": self.last_occurrence_time,
            "next_occurrence_time": self.next_occurrence_time,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleRecord:
        return cls(
            schedule_id=data["schedule_id"],
            tenant_id=data.get("tenant_id", "default-tenant"),
            workspace_id=data.get("workspace_id", "default-workspace"),
            project_id=data.get("project_id"),
            migration_id=data["migration_id"],
            operation_type=data.get("operation_type", "migration.start"),
            schedule_type=ScheduleType(data.get("schedule_type", "RECURRING")),
            cron_expression=data.get("cron_expression", "0 * * * *"),
            one_shot_time=data.get("one_shot_time"),
            timezone=data.get("timezone", "UTC"),
            state=ScheduleLifecycleState(data["state"]),
            enabled=bool(data.get("enabled", True)),
            revision=int(data.get("revision", 1)),
            misfire_policy=MisfirePolicy(data.get("misfire_policy", "SKIP")),
            overlap_policy=OverlapPolicy(data.get("overlap_policy", "REJECT_OVERLAP")),
            activation_id=data.get("activation_id"),
            creator_actor_id=data.get("creator_actor_id"),
            delegated_roles=data.get("delegated_roles"),
            last_occurrence_time=data.get("last_occurrence_time"),
            next_occurrence_time=data.get("next_occurrence_time"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ScheduleOccurrenceRecord:
    occurrence_id: str
    schedule_id: str
    canonical_scheduled_time: str
    status: OccurrenceStatus = OccurrenceStatus.PENDING
    tenant_id: str = "default-tenant"
    workspace_id: str = "default-workspace"
    project_id: Optional[str] = None
    schedule_revision: int = 1
    claim_attempt_id: Optional[str] = None
    claim_owner_id: Optional[str] = None
    lease_id: Optional[str] = None
    fence_epoch: int = 1
    dispatched_at: Optional[str] = None
    dispatched_command_id: Optional[str] = None
    dispatched_operation_id: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[str] = None
    error_payload: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "occurrence_id": self.occurrence_id,
            "schedule_id": self.schedule_id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "schedule_revision": self.schedule_revision,
            "canonical_scheduled_time": self.canonical_scheduled_time,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "claim_attempt_id": self.claim_attempt_id,
            "claim_owner_id": self.claim_owner_id,
            "lease_id": self.lease_id,
            "fence_epoch": self.fence_epoch,
            "dispatched_at": self.dispatched_at,
            "dispatched_command_id": self.dispatched_command_id,
            "dispatched_operation_id": self.dispatched_operation_id,
            "completed_at": self.completed_at,
            "result_summary": self.result_summary,
            "error_payload": self.error_payload,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleOccurrenceRecord:
        err = data.get("error_payload")
        if isinstance(err, str):
            try:
                err = json.loads(err)
            except Exception:
                err = {"raw": err}

        return cls(
            occurrence_id=data["occurrence_id"],
            schedule_id=data["schedule_id"],
            tenant_id=data.get("tenant_id", "default-tenant"),
            workspace_id=data.get("workspace_id", "default-workspace"),
            project_id=data.get("project_id"),
            schedule_revision=int(data.get("schedule_revision", 1)),
            canonical_scheduled_time=data["canonical_scheduled_time"],
            status=OccurrenceStatus(data["status"]),
            claim_attempt_id=data.get("claim_attempt_id"),
            claim_owner_id=data.get("claim_owner_id"),
            lease_id=data.get("lease_id"),
            fence_epoch=int(data.get("fence_epoch", 1)),
            dispatched_at=data.get("dispatched_at"),
            dispatched_command_id=data.get("dispatched_command_id"),
            dispatched_operation_id=data.get("dispatched_operation_id"),
            completed_at=data.get("completed_at"),
            result_summary=data.get("result_summary"),
            error_payload=err,
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


def compute_occurrence_id(schedule_id: str, revision: int, scheduled_time_iso: str) -> str:
    """Deterministic occurrence identity based on schedule ID, revision, and canonical scheduled time instant."""
    # Clean ISO string to create deterministic, safe ID
    clean_instant = scheduled_time_iso.replace(":", "").replace("-", "").replace("+", "Z")
    return f"occ_{schedule_id}_r{revision}_{clean_instant}"


class ScheduleService:
    def __init__(self, lease_manager: Optional[LeaseManager] = None) -> None:
        self.lease_manager = lease_manager or LeaseManager()

    def create_schedule(self, schedule: ScheduleRecord, conn: sqlite3.Connection) -> ScheduleRecord:
        """Create and persist a new schedule record with validated recurrence and timezone."""
        validate_timezone(schedule.timezone)
        if schedule.schedule_type == ScheduleType.RECURRING:
            validate_cron_expression(schedule.cron_expression)
            if not schedule.next_occurrence_time:
                schedule.next_occurrence_time = compute_next_occurrence(
                    schedule.cron_expression, schedule.timezone
                )
        elif schedule.schedule_type == ScheduleType.ONE_TIME:
            if not schedule.one_shot_time:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "one_shot_time is required for ONE_TIME schedule.")
            schedule.next_occurrence_time = schedule.one_shot_time

        now = datetime.now(timezone.utc).isoformat()
        schedule.created_at = now
        schedule.updated_at = now

        conn.execute(
            """
            INSERT INTO schedules (
                schedule_id, tenant_id, workspace_id, project_id, migration_id,
                operation_type, schedule_type, cron_expression, one_shot_time,
                timezone, state, enabled, revision, misfire_policy, overlap_policy,
                activation_id, creator_actor_id, delegated_roles,
                last_occurrence_time, next_occurrence_time, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schedule.schedule_id,
                schedule.tenant_id,
                schedule.workspace_id,
                schedule.project_id,
                schedule.migration_id,
                schedule.operation_type,
                schedule.schedule_type.value if hasattr(schedule.schedule_type, "value") else str(schedule.schedule_type),
                schedule.cron_expression,
                schedule.one_shot_time,
                schedule.timezone,
                schedule.state.value if hasattr(schedule.state, "value") else str(schedule.state),
                1 if schedule.enabled else 0,
                schedule.revision,
                schedule.misfire_policy.value if hasattr(schedule.misfire_policy, "value") else str(schedule.misfire_policy),
                schedule.overlap_policy.value if hasattr(schedule.overlap_policy, "value") else str(schedule.overlap_policy),
                schedule.activation_id,
                schedule.creator_actor_id,
                schedule.delegated_roles,
                schedule.last_occurrence_time,
                schedule.next_occurrence_time,
                schedule.created_at,
                schedule.updated_at,
            ),
        )
        return schedule

    def update_schedule(
        self,
        schedule_id: str,
        conn: sqlite3.Connection,
        cron_expression: Optional[str] = None,
        timezone_str: Optional[str] = None,
        misfire_policy: Optional[MisfirePolicy] = None,
        overlap_policy: Optional[OverlapPolicy] = None,
        one_shot_time: Optional[str] = None,
    ) -> ScheduleRecord:
        """Update an existing schedule with monotonic revision increment and recurrence recalculation."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        new_cron = cron_expression or sch.cron_expression
        new_tz = timezone_str or sch.timezone
        new_misfire = misfire_policy or sch.misfire_policy
        new_overlap = overlap_policy or sch.overlap_policy
        new_one_shot = one_shot_time if one_shot_time is not None else sch.one_shot_time

        validate_timezone(new_tz)
        if sch.schedule_type == ScheduleType.RECURRING:
            validate_cron_expression(new_cron)
            next_occ = compute_next_occurrence(new_cron, new_tz)
        else:
            next_occ = new_one_shot

        new_rev = sch.revision + 1
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            UPDATE schedules SET
                cron_expression = ?, timezone = ?, misfire_policy = ?, overlap_policy = ?,
                one_shot_time = ?, revision = ?, next_occurrence_time = ?, updated_at = ?
            WHERE schedule_id = ?
            """,
            (
                new_cron,
                new_tz,
                new_misfire.value if hasattr(new_misfire, "value") else str(new_misfire),
                new_overlap.value if hasattr(new_overlap, "value") else str(new_overlap),
                new_one_shot,
                new_rev,
                next_occ,
                now,
                schedule_id,
            ),
        )
        return self.get_by_id(schedule_id, conn)

    def arm_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> ScheduleRecord:
        """Arm a schedule for active occurrence generation."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")
        ScheduleLifecycleMachine.validate_transition(sch.state, ScheduleLifecycleState.ARMED)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE schedules SET state = ?, enabled = 1, updated_at = ? WHERE schedule_id = ?",
            (ScheduleLifecycleState.ARMED.value, now, schedule_id),
        )
        return self.get_by_id(schedule_id, conn)

    def disable_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> ScheduleRecord:
        """Disable future occurrences without cancelling active migrations."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE schedules SET enabled = 0, updated_at = ? WHERE schedule_id = ?",
            (now, schedule_id),
        )
        return self.get_by_id(schedule_id, conn)

    def enable_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> ScheduleRecord:
        """Re-enable schedule for future occurrence generation."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE schedules SET enabled = 1, updated_at = ? WHERE schedule_id = ?",
            (now, schedule_id),
        )
        return self.get_by_id(schedule_id, conn)

    def cancel_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> ScheduleRecord:
        """Transition schedule to CANCELLED state."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")
        ScheduleLifecycleMachine.validate_transition(sch.state, ScheduleLifecycleState.CANCELLED)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE schedules SET state = ?, enabled = 0, updated_at = ? WHERE schedule_id = ?",
            (ScheduleLifecycleState.CANCELLED.value, now, schedule_id),
        )
        return self.get_by_id(schedule_id, conn)

    def delete_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> bool:
        """Delete schedule intent. Preserves historical occurrences."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")
        cur = conn.execute("DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,))
        return cur.rowcount > 0

    def get_by_id(self, schedule_id: str, conn: sqlite3.Connection) -> Optional[ScheduleRecord]:
        cur = conn.execute("SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_schedule(row)

    def list_schedules(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[ScheduleRecord]:
        query = "SELECT * FROM schedules WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if workspace_id:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " ORDER BY created_at DESC"
        cur = conn.execute(query, tuple(params))
        return [self._row_to_schedule(r) for r in cur.fetchall()]

    def materialize_due_occurrences(
        self,
        conn: sqlite3.Connection,
        current_time_iso: Optional[str] = None,
    ) -> List[ScheduleOccurrenceRecord]:
        """Scan armed & enabled schedules for due occurrences, materialize them durably, and advance next_occurrence_time."""
        now_iso = current_time_iso or datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            SELECT * FROM schedules
            WHERE state = ? AND enabled = 1 AND next_occurrence_time IS NOT NULL AND next_occurrence_time <= ?
            ORDER BY next_occurrence_time ASC
            """,
            (ScheduleLifecycleState.ARMED.value, now_iso),
        )
        schedules = [self._row_to_schedule(r) for r in cur.fetchall()]
        materialized: List[ScheduleOccurrenceRecord] = []

        for sch in schedules:
            sched_time = sch.next_occurrence_time
            if not sched_time:
                continue

            occ_id = compute_occurrence_id(sch.schedule_id, sch.revision, sched_time)
            # Check if occurrence record already exists (idempotent materialization)
            existing = self.get_occurrence_by_id(occ_id, conn)
            if existing is None:
                occ = ScheduleOccurrenceRecord(
                    occurrence_id=occ_id,
                    schedule_id=sch.schedule_id,
                    tenant_id=sch.tenant_id,
                    workspace_id=sch.workspace_id,
                    project_id=sch.project_id,
                    schedule_revision=sch.revision,
                    canonical_scheduled_time=sched_time,
                    status=OccurrenceStatus.PENDING,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO schedule_occurrences (
                        occurrence_id, schedule_id, tenant_id, workspace_id, project_id,
                        schedule_revision, canonical_scheduled_time, status,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        occ.occurrence_id,
                        occ.schedule_id,
                        occ.tenant_id,
                        occ.workspace_id,
                        occ.project_id,
                        occ.schedule_revision,
                        occ.canonical_scheduled_time,
                        occ.status.value,
                        occ.created_at,
                        occ.updated_at,
                    ),
                )
                materialized.append(occ)
            else:
                materialized.append(existing)

            # Advance next occurrence on schedule
            if sch.schedule_type == ScheduleType.RECURRING:
                next_time = compute_next_occurrence(sch.cron_expression, sch.timezone)
                conn.execute(
                    "UPDATE schedules SET last_occurrence_time = ?, next_occurrence_time = ?, updated_at = ? WHERE schedule_id = ?",
                    (sched_time, next_time, now_iso, sch.schedule_id),
                )
            else:
                # One-time schedule consumed
                conn.execute(
                    "UPDATE schedules SET last_occurrence_time = ?, next_occurrence_time = NULL, state = ?, enabled = 0, updated_at = ? WHERE schedule_id = ?",
                    (sched_time, ScheduleLifecycleState.CONSUMED.value, now_iso, sch.schedule_id),
                )

        return materialized

    def claim_occurrence(
        self,
        occurrence_id: str,
        owner_id: str,
        attempt_id: str,
        conn: sqlite3.Connection,
        lease_duration_seconds: int = 60,
    ) -> ExecutionLease:
        """Acquire lease-fenced ownership over a pending or expired occurrence. Fails closed if actively claimed by another owner."""
        occ = self.get_occurrence_by_id(occurrence_id, conn)
        if occ is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Occurrence {occurrence_id!r} not found.")

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_at_iso = (now + datetime.timedelta(seconds=lease_duration_seconds)).isoformat() if hasattr(datetime, "timedelta") else now_iso

        from datetime import timedelta
        expires_at_iso = (now + timedelta(seconds=lease_duration_seconds)).isoformat()

        # If already terminal
        if occ.status in (OccurrenceStatus.COMPLETED, OccurrenceStatus.FAILED, OccurrenceStatus.MISFIRED, OccurrenceStatus.SKIPPED_OVERLAP):
            raise PipelineError(
                PipelineErrorCode.CONFLICT,
                f"Occurrence {occurrence_id!r} is already in terminal status {occ.status.value!r}.",
            )

        # Acquire execution lease using canonical LeaseManager
        lease_id = f"lease-occ-{uuid.uuid4().hex[:12]}"
        init_fp = f"fp-occ-{occurrence_id}"
        lease = self.lease_manager.acquire_lease(
            lease_id=lease_id,
            attempt_id=attempt_id,
            owner_id=owner_id,
            expires_at=expires_at_iso,
            initialization_fingerprint=init_fp,
            conn=conn,
        )

        # Update occurrence status to CLAIMED
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, claim_attempt_id = ?, claim_owner_id = ?,
                lease_id = ?, fence_epoch = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (
                OccurrenceStatus.CLAIMED.value,
                attempt_id,
                owner_id,
                lease.lease_id,
                lease.fence_epoch,
                now_iso,
                occurrence_id,
            ),
        )
        return lease

    def mark_dispatched(
        self,
        occurrence_id: str,
        command_id: str,
        lease_id: str,
        fence_epoch: int,
        conn: sqlite3.Connection,
    ) -> None:
        """Mark occurrence as dispatched. Validates fence epoch and lease identity."""
        occ = self.get_occurrence_by_id(occurrence_id, conn)
        if occ is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Occurrence {occurrence_id!r} not found.")

        if occ.claim_attempt_id:
            self.lease_manager.validate_lease(occ.claim_attempt_id, lease_id, fence_epoch, conn)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, dispatched_command_id = ?, dispatched_at = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (OccurrenceStatus.DISPATCHED.value, command_id, now_iso, now_iso, occurrence_id),
        )

    def mark_completed(
        self,
        occurrence_id: str,
        operation_id: str,
        result_summary: str,
        lease_id: str,
        fence_epoch: int,
        conn: sqlite3.Connection,
    ) -> None:
        """Mark occurrence as completed. Validates lease and fence epoch."""
        occ = self.get_occurrence_by_id(occurrence_id, conn)
        if occ is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Occurrence {occurrence_id!r} not found.")

        if occ.claim_attempt_id:
            self.lease_manager.validate_lease(occ.claim_attempt_id, lease_id, fence_epoch, conn)

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, dispatched_operation_id = ?, completed_at = ?, result_summary = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (OccurrenceStatus.COMPLETED.value, operation_id, now_iso, result_summary, now_iso, occurrence_id),
        )

    def mark_failed(
        self,
        occurrence_id: str,
        error_details: Dict[str, Any],
        conn: sqlite3.Connection,
        lease_id: Optional[str] = None,
        fence_epoch: Optional[int] = None,
    ) -> None:
        """Mark occurrence as failed with structured error payload."""
        occ = self.get_occurrence_by_id(occurrence_id, conn)
        if occ is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Occurrence {occurrence_id!r} not found.")

        if occ.claim_attempt_id and lease_id and fence_epoch is not None:
            try:
                self.lease_manager.validate_lease(occ.claim_attempt_id, lease_id, fence_epoch, conn)
            except LeaseConflictError:
                pass  # Recording failure state even if lease lapsed

        now_iso = datetime.now(timezone.utc).isoformat()
        err_json = json.dumps(error_details) if isinstance(error_details, dict) else str(error_details)
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, error_payload = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (OccurrenceStatus.FAILED.value, err_json, now_iso, occurrence_id),
        )

    def mark_misfired(self, occurrence_id: str, reason: str, conn: sqlite3.Connection) -> None:
        """Mark occurrence as misfired according to schedule misfire policy."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, result_summary = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (OccurrenceStatus.MISFIRED.value, reason, now_iso, occurrence_id),
        )

    def mark_skipped_overlap(self, occurrence_id: str, active_migration_id: str, conn: sqlite3.Connection) -> None:
        """Mark occurrence as skipped due to active overlapping execution."""
        now_iso = datetime.now(timezone.utc).isoformat()
        summary = f"Skipped overlap: Migration {active_migration_id!r} currently in active lifecycle execution."
        conn.execute(
            """
            UPDATE schedule_occurrences SET
                status = ?, result_summary = ?, updated_at = ?
            WHERE occurrence_id = ?
            """,
            (OccurrenceStatus.SKIPPED_OVERLAP.value, summary, now_iso, occurrence_id),
        )

    def get_occurrence_by_id(self, occurrence_id: str, conn: sqlite3.Connection) -> Optional[ScheduleOccurrenceRecord]:
        cur = conn.execute("SELECT * FROM schedule_occurrences WHERE occurrence_id = ?", (occurrence_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ScheduleOccurrenceRecord.from_dict(dict(row))

    def list_occurrences(
        self,
        schedule_id: str,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[ScheduleOccurrenceRecord]:
        cur = conn.execute(
            "SELECT * FROM schedule_occurrences WHERE schedule_id = ? ORDER BY canonical_scheduled_time DESC LIMIT ?",
            (schedule_id, limit),
        )
        return [ScheduleOccurrenceRecord.from_dict(dict(r)) for r in cur.fetchall()]

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> ScheduleRecord:
        return ScheduleRecord(
            schedule_id=row["schedule_id"],
            tenant_id=row["tenant_id"],
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            migration_id=row["migration_id"],
            operation_type=row["operation_type"],
            schedule_type=ScheduleType(row["schedule_type"]),
            cron_expression=row["cron_expression"],
            one_shot_time=row["one_shot_time"],
            timezone=row["timezone"],
            state=ScheduleLifecycleState(row["state"]),
            enabled=bool(row["enabled"]),
            revision=int(row["revision"]),
            misfire_policy=MisfirePolicy(row["misfire_policy"]),
            overlap_policy=OverlapPolicy(row["overlap_policy"]),
            activation_id=row["activation_id"],
            creator_actor_id=row["creator_actor_id"],
            delegated_roles=row["delegated_roles"],
            last_occurrence_time=row["last_occurrence_time"],
            next_occurrence_time=row["next_occurrence_time"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
