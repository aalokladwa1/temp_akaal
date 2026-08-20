"""akaalPipeline.operations.schedules
===================================
Durable schedule lifecycle & activation admission service.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from akaalPipeline.contracts.enums import ScheduleLifecycleState
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.state.lifecycle import ScheduleLifecycleMachine


@dataclass
class ScheduleRecord:
    schedule_id: str
    migration_id: str
    cron_expression: str
    state: ScheduleLifecycleState
    activation_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "migration_id": self.migration_id,
            "cron_expression": self.cron_expression,
            "state": self.state.value,
            "activation_id": self.activation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleRecord:
        return cls(
            schedule_id=data["schedule_id"],
            migration_id=data["migration_id"],
            cron_expression=data["cron_expression"],
            state=ScheduleLifecycleState(data["state"]),
            activation_id=data.get("activation_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


class ScheduleService:
    def create_schedule(self, schedule: ScheduleRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO schedules (schedule_id, migration_id, cron_expression, state, activation_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schedule.schedule_id,
                schedule.migration_id,
                schedule.cron_expression,
                schedule.state.value,
                schedule.activation_id,
                schedule.created_at,
                schedule.updated_at,
            ),
        )

    def arm_schedule(self, schedule_id: str, conn: sqlite3.Connection) -> None:
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found")
        ScheduleLifecycleMachine.validate_transition(sch.state, ScheduleLifecycleState.ARMED)
        conn.execute(
            "UPDATE schedules SET state = ?, updated_at = ? WHERE schedule_id = ?",
            (ScheduleLifecycleState.ARMED.value, datetime.now(timezone.utc).isoformat(), schedule_id),
        )

    def activate_schedule(self, schedule_id: str, activation_id: str, conn: sqlite3.Connection) -> bool:
        """Attempt activation. Returns True if activation succeeded (exactly once), False if already activating/consumed."""
        sch = self.get_by_id(schedule_id, conn)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found")

        if sch.state != ScheduleLifecycleState.ARMED:
            return False

        cur = conn.execute(
            "UPDATE schedules SET state = ?, activation_id = ?, updated_at = ? WHERE schedule_id = ? AND state = ?",
            (
                ScheduleLifecycleState.ACTIVATING.value,
                activation_id,
                datetime.now(timezone.utc).isoformat(),
                schedule_id,
                ScheduleLifecycleState.ARMED.value,
            ),
        )
        return cur.rowcount > 0

    def get_by_id(self, schedule_id: str, conn: sqlite3.Connection) -> Optional[ScheduleRecord]:
        cur = conn.execute("SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ScheduleRecord.from_dict(
            {
                "schedule_id": row["schedule_id"],
                "migration_id": row["migration_id"],
                "cron_expression": row["cron_expression"],
                "state": row["state"],
                "activation_id": row["activation_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
