"""akaalPipeline.validation.continuous
====================================
Continuous Validation Service for ongoing mission lifecycle, change stream integration, overlap prevention, and restart recovery.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.validation.models import (
    ValidationMissionRecord,
    ValidationMissionState,
)

logger = logging.getLogger("akaalPipeline.validation.continuous")


class ContinuousValidationService:
    """
    Continuous Validation Lifecycle & Execution Manager.
    Orchestrates ongoing validation missions with controlled execution semantics:
    - Zero infinite busy loop.
    - Explicit overlap policy (REJECT_OVERLAP: skips if an evaluation cycle is already active).
    - Lifecycle states: INITIALIZED -> RUNNING <-> PAUSED -> COMPLETED / CANCELLED / FAILED.
    - Change-aware evaluation using CDC positions (Oracle SCN, Postgres LSN, MySQL GTID, Kafka offsets) or scheduled cycles.
    - Durable SQLite state recovery on process restart.
    - Strictly non-mutating (zero automatic data repair).
    """

    def __init__(self, lease_manager: Optional[LeaseManager] = None) -> None:
        self.lease_manager = lease_manager or LeaseManager()
        self._active_evaluations: Dict[str, bool] = {}
        self._lock = Lock()

    def start_continuous_mission(
        self,
        mission: ValidationMissionRecord,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        """Starts a continuous validation mission."""
        actor.enforce_resource_scope(
            resource_tenant_id=mission.tenant_id,
            resource_workspace_id=mission.workspace_id,
            resource_project_id=mission.project_id,
            resource_kind="ValidationMission",
            resource_id=mission.mission_id,
        )

        if mission.state in (ValidationMissionState.CANCELLED, ValidationMissionState.COMPLETED):
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Cannot start continuous mission {mission.mission_id!r} in terminal state {mission.state.value!r}.",
            )

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.RUNNING
        mission.is_continuous = True
        mission.updated_at = now

        self._update_mission_state(mission, conn)
        logger.info(f"Continuous validation mission {mission.mission_id!r} STARTED by actor {actor.actor_id!r}.")
        return mission

    def pause_continuous_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        """Pauses a running continuous validation mission."""
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Mission {mission_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=mission.tenant_id,
            resource_workspace_id=mission.workspace_id,
            resource_project_id=mission.project_id,
            resource_kind="ValidationMission",
            resource_id=mission.mission_id,
        )

        if mission.state != ValidationMissionState.RUNNING:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Cannot pause continuous mission {mission_id!r} in state {mission.state.value!r}. Must be RUNNING.",
            )

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.PAUSED
        mission.updated_at = now

        self._update_mission_state(mission, conn)
        logger.info(f"Continuous validation mission {mission_id!r} PAUSED.")
        return mission

    def resume_continuous_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        """Resumes a paused continuous validation mission."""
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Mission {mission_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=mission.tenant_id,
            resource_workspace_id=mission.workspace_id,
            resource_project_id=mission.project_id,
            resource_kind="ValidationMission",
            resource_id=mission.mission_id,
        )

        if mission.state != ValidationMissionState.PAUSED:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Cannot resume continuous mission {mission_id!r} in state {mission.state.value!r}. Must be PAUSED.",
            )

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.RUNNING
        mission.updated_at = now

        self._update_mission_state(mission, conn)
        logger.info(f"Continuous validation mission {mission_id!r} RESUMED.")
        return mission

    def cancel_continuous_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        reason: str = "Operator cancelled",
    ) -> ValidationMissionRecord:
        """Cancels a continuous validation mission."""
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Mission {mission_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=mission.tenant_id,
            resource_workspace_id=mission.workspace_id,
            resource_project_id=mission.project_id,
            resource_kind="ValidationMission",
            resource_id=mission.mission_id,
        )

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.CANCELLED
        mission.updated_at = now

        self._update_mission_state(mission, conn)
        logger.info(f"Continuous validation mission {mission_id!r} CANCELLED. Reason: {reason}")
        return mission

    def execute_evaluation_cycle(
        self,
        mission_id: str,
        conn: sqlite3.Connection,
        evaluator_fn: Any,
        change_position: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Executes a single continuous validation evaluation cycle with REJECT_OVERLAP policy protection.
        If an evaluation cycle for this mission is currently in progress, skips evaluation cleanly.
        """
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            return False, None, f"Mission {mission_id!r} not found."

        if mission.state != ValidationMissionState.RUNNING:
            return False, None, f"Mission {mission_id!r} is not RUNNING (current state: {mission.state.value})."

        with self._lock:
            if self._active_evaluations.get(mission_id, False):
                logger.warning(f"REJECT_OVERLAP: Continuous validation cycle for mission {mission_id!r} skipped because previous cycle is still active.")
                return False, None, "SKIPPED_OVERLAP: Evaluation cycle currently active."
            self._active_evaluations[mission_id] = True

        try:
            now = datetime.now(timezone.utc).isoformat()
            # Execute validation pass through canonical authority
            eval_result = evaluator_fn(mission, change_position)

            is_pass = eval_result.get("status") == "SUCCESS" and eval_result.get("rows_mismatched", 0) == 0

            mission.evaluation_count += 1
            if is_pass:
                mission.pass_count += 1
                mission.last_result_status = "SUCCESS"
            else:
                mission.fail_count += 1
                mission.last_result_status = "MISMATCH"

            mission.last_evaluated_at = now
            if change_position:
                mission.last_change_position = change_position
            mission.updated_at = now

            self._update_mission_state(mission, conn)
            return True, eval_result, "SUCCESS" if is_pass else "MISMATCH"
        except Exception as ex:
            mission.evaluation_count += 1
            mission.fail_count += 1
            mission.last_result_status = "ERROR"
            mission.updated_at = datetime.now(timezone.utc).isoformat()
            self._update_mission_state(mission, conn)
            logger.error(f"Continuous evaluation error for mission {mission_id!r}: {ex}")
            return False, {"error": str(ex)}, f"ERROR: {ex}"
        finally:
            with self._lock:
                self._active_evaluations[mission_id] = False

    def recover_on_restart(self, conn: sqlite3.Connection) -> List[ValidationMissionRecord]:
        """
        Scans durable SQLite store for RUNNING or PAUSED continuous missions after process restart,
        reconstructing in-memory tracker state and returning active missions.
        """
        cur = conn.execute(
            "SELECT * FROM validation_missions WHERE is_continuous = 1 AND state IN (?, ?)",
            (ValidationMissionState.RUNNING.value, ValidationMissionState.PAUSED.value),
        )
        recovered = [ValidationMissionRecord.from_dict(dict(r)) for r in cur.fetchall()]
        logger.info(f"Continuous validation service recovered {len(recovered)} active/paused continuous missions after restart.")
        return recovered

    def get_mission_by_id(self, mission_id: str, conn: sqlite3.Connection) -> Optional[ValidationMissionRecord]:
        cur = conn.execute("SELECT * FROM validation_missions WHERE mission_id = ?", (mission_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ValidationMissionRecord.from_dict(dict(row))

    def _update_mission_state(self, mission: ValidationMissionRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            UPDATE validation_missions SET
                state = ?, is_continuous = ?, baseline_id = ?, schedule_id = ?,
                last_evaluated_at = ?, last_change_position = ?,
                evaluation_count = ?, pass_count = ?, fail_count = ?,
                last_result_status = ?, updated_at = ?
            WHERE mission_id = ?
            """,
            (
                mission.state.value if hasattr(mission.state, "value") else str(mission.state),
                1 if mission.is_continuous else 0,
                mission.baseline_id,
                mission.schedule_id,
                mission.last_evaluated_at,
                mission.last_change_position,
                mission.evaluation_count,
                mission.pass_count,
                mission.fail_count,
                mission.last_result_status,
                mission.updated_at,
                mission.mission_id,
            ),
        )
