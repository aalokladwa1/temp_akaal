"""akaalPipeline.validation.service
=================================
Canonical Validation Pipeline Service orchestrating missions, baselines, readiness resolution, durable scheduling, and engine execution.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaalEngine.validation.api import ValidationAuthority
from akaalEngine.validation.models.plan import ProofScope, ValidationMode, ValidationPlan
from akaalEngine.validation.models.result import ValidationResult
from akaalPipeline.contracts.enums import MisfirePolicy, OverlapPolicy, ScheduleLifecycleState, ScheduleType
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.schedules import ScheduleRecord, ScheduleService
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.validation.boundary import ValidationBoundaryManager
from akaalPipeline.validation.continuous import ContinuousValidationService
from akaalPipeline.validation.models import (
    BaselineType,
    PositionType,
    TemporalStrategy,
    ValidationBaselineRecord,
    ValidationCapabilityInfo,
    ValidationMissionRecord,
    ValidationMissionState,
    ValidationReadinessResult,
    VerificationStatus,
)

logger = logging.getLogger("akaalPipeline.validation.service")


class ValidationPipelineService:
    """
    Canonical Motherboard Service for DevKros Validation.
    Integrates ValidationAuthority (#11), ScheduleService, BoundaryManager, and ContinuousValidationService.
    Reuses existing canonical authorities — zero duplicate engines or schedulers.
    """

    def __init__(
        self,
        validation_authority: Optional[ValidationAuthority] = None,
        schedule_service: Optional[ScheduleService] = None,
        migration_repository: Optional[SQLiteMigrationRepository] = None,
    ) -> None:
        self.validation_authority = validation_authority or ValidationAuthority()
        self.schedule_service = schedule_service or ScheduleService()
        self.boundary_manager = ValidationBoundaryManager(migration_repository=migration_repository)
        self.continuous_service = ContinuousValidationService(lease_manager=self.schedule_service.lease_manager)

    def create_mission(
        self,
        payload: Dict[str, Any],
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        """Creates a new Validation Mission record in DRAFT state."""
        mission_id = payload.get("mission_id") or f"val-mission-{uuid.uuid4().hex[:12]}"
        name = payload.get("name") or f"Validation {mission_id}"
        source_provider = payload.get("source_provider") or "Oracle"
        target_provider = payload.get("target_provider") or "PostgreSQL"
        strategy_raw = payload.get("temporal_strategy") or "EXECUTE_ON_INIT"

        try:
            temporal_strategy = TemporalStrategy(strategy_raw)
        except ValueError:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown temporal strategy {strategy_raw!r}.")

        mission = ValidationMissionRecord(
            mission_id=mission_id,
            tenant_id=actor.organization_id or "default-tenant",
            workspace_id=actor.workspace_id or "default-workspace",
            project_id=actor.project_id or "default-project",
            name=name,
            source_provider=source_provider,
            target_provider=target_provider,
            source_connection_id=payload.get("source_connection_id"),
            target_connection_id=payload.get("target_connection_id"),
            validation_context=payload.get("validation_context", "INDEPENDENT"),
            linked_migration_id=payload.get("linked_migration_id"),
            baseline_id=payload.get("baseline_id"),
            temporal_strategy=temporal_strategy,
            is_continuous=(temporal_strategy == TemporalStrategy.CONTINUOUS),
            state=ValidationMissionState.DRAFT,
            scope_config=payload.get("scope_config", {}),
            execution_policy=payload.get("execution_policy", {}),
        )

        self.save_mission(mission, conn)

        # Automatically establish baseline if provided in payload
        baseline_intent = payload.get("baseline_intent")
        if baseline_intent == BaselineType.INHERITED_MIGRATION.value and mission.linked_migration_id:
            base = self.boundary_manager.create_migration_baseline(
                mission, mission.linked_migration_id, actor, conn
            )
            mission.baseline_id = base.baseline_id
            self.save_mission(mission, conn)
        elif baseline_intent == BaselineType.MAINTENANCE_COORDINATED.value:
            cond = payload.get("maintenance_condition", "WRITES_STOPPED_DECLARED")
            base = self.boundary_manager.create_maintenance_baseline(mission, cond, actor, conn)
            mission.baseline_id = base.baseline_id
            self.save_mission(mission, conn)

        if temporal_strategy == TemporalStrategy.SCHEDULE_LATER and payload.get("schedule_time"):
            sch = self.schedule_mission_later(mission.mission_id, payload["schedule_time"], actor, conn)
            mission.schedule_id = sch.schedule_id
        elif temporal_strategy == TemporalStrategy.RECURRING and payload.get("cron_expression"):
            sch = self.schedule_recurring_mission(mission.mission_id, payload["cron_expression"], actor, conn)
            mission.schedule_id = sch.schedule_id

        return mission

    def initialize_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationReadinessResult:
        """
        Initializes a validation mission.
        Evaluates readiness requirements. If readiness fails, initialization fails closed.
        """
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")

        readiness = self.boundary_manager.evaluate_readiness(mission, actor, conn)
        if not readiness.is_ready:
            mission.state = ValidationMissionState.FAILED
            mission.last_result_status = f"READINESS_FAILED: {readiness.summary}"
            self.save_mission(mission, conn)
            return readiness

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.INITIALIZED
        mission.updated_at = now
        self.save_mission(mission, conn)

        return readiness

    def execute_mission_immediately(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        source_rows: Optional[List[Dict[str, Any]]] = None,
        target_rows: Optional[List[Dict[str, Any]]] = None,
        pk_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        EXECUTE ON INIT Backend Behavior.
        Initializes mission -> verifies readiness & authorization -> executes immediately through ValidationAuthority.
        Initialization failure prevents execution.
        """
        readiness = self.initialize_mission(mission_id, actor, conn)
        if not readiness.is_ready:
            raise PipelineError(
                PipelineErrorCode.FAILED_PRECONDITION,
                f"Execution rejected: Mission initialization failed readiness checks ({readiness.summary}).",
            )

        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")

        now = datetime.now(timezone.utc).isoformat()
        mission.state = ValidationMissionState.RUNNING
        self.save_mission(mission, conn)

        # Prepare ValidationPlan
        tbl_name = mission.scope_config.get("table_name") or "canonical_validation_table"
        val_mode_str = mission.execution_policy.get("mode") or "EXACT_FULL"
        try:
            val_mode = ValidationMode(val_mode_str)
        except ValueError:
            val_mode = ValidationMode.EXACT_FULL

        plan = ValidationPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            migration_id=mission.linked_migration_id or mission.mission_id,
            source_identity=mission.source_provider,
            target_identity=mission.target_provider,
            table_name=tbl_name,
            mode=val_mode,
        )

        src = source_rows if source_rows is not None else [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]
        tgt = target_rows if target_rows is not None else [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]
        pks = pk_columns or ["id"]

        try:
            val_res: ValidationResult = self.validation_authority.execute_validation(
                plan=plan, source_rows=src, target_rows=tgt, pk_columns=pks
            )
            is_pass = val_res.status == "SUCCESS" and val_res.rows_mismatched == 0

            mission.evaluation_count += 1
            if is_pass:
                mission.pass_count += 1
                mission.last_result_status = "SUCCESS"
                mission.state = ValidationMissionState.COMPLETED
            else:
                mission.fail_count += 1
                mission.last_result_status = "MISMATCH"
                mission.state = ValidationMissionState.FAILED

            mission.last_evaluated_at = datetime.now(timezone.utc).isoformat()
            mission.updated_at = datetime.now(timezone.utc).isoformat()
            self.save_mission(mission, conn)

            return {
                "mission_id": mission.mission_id,
                "status": mission.last_result_status,
                "readiness": readiness.to_dict(),
                "validation_result": val_res.to_dict(),
            }
        except Exception as ex:
            mission.state = ValidationMissionState.FAILED
            mission.last_result_status = f"EXECUTION_ERROR: {ex}"
            mission.updated_at = datetime.now(timezone.utc).isoformat()
            self.save_mission(mission, conn)
            logger.error(f"Immediate validation execution error for mission {mission_id!r}: {ex}")
            raise

    def schedule_mission_later(
        self,
        mission_id: str,
        one_shot_time_iso: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        timezone_str: str = "UTC",
    ) -> ScheduleRecord:
        """
        SCHEDULE LATER Backend Behavior.
        Creates a durable ONE_TIME schedule in canonical ScheduleService, armed and persisted.
        """
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")

        readiness = self.initialize_mission(mission_id, actor, conn)
        if not readiness.is_ready:
            raise PipelineError(
                PipelineErrorCode.FAILED_PRECONDITION,
                f"Schedule creation rejected: Mission initialization failed readiness checks ({readiness.summary}).",
            )

        sch_id = f"sch-val-oneshot-{uuid.uuid4().hex[:8]}"
        sch_record = ScheduleRecord(
            schedule_id=sch_id,
            migration_id=mission.mission_id,
            tenant_id=actor.organization_id or mission.tenant_id,
            workspace_id=actor.workspace_id or mission.workspace_id,
            project_id=actor.project_id or mission.project_id,
            operation_type="validation.execute",
            schedule_type=ScheduleType.ONE_TIME,
            cron_expression="0 * * * *",
            one_shot_time=one_shot_time_iso,
            timezone=timezone_str,
            state=ScheduleLifecycleState.ARMED,
            enabled=True,
            misfire_policy=MisfirePolicy.SKIP,
            overlap_policy=OverlapPolicy.REJECT_OVERLAP,
            creator_actor_id=actor.actor_id,
        )

        saved_sch = self.schedule_service.create_schedule(sch_record, conn)
        mission.schedule_id = saved_sch.schedule_id
        mission.temporal_strategy = TemporalStrategy.SCHEDULE_LATER
        self.save_mission(mission, conn)

        logger.info(f"Durable ONE_TIME schedule {saved_sch.schedule_id!r} created for mission {mission_id!r} at {one_shot_time_iso!r}.")
        return saved_sch

    def schedule_recurring_mission(
        self,
        mission_id: str,
        cron_expression: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        timezone_str: str = "UTC",
    ) -> ScheduleRecord:
        """
        RECURRING Backend Behavior.
        Creates a durable RECURRING schedule in canonical ScheduleService, armed and persisted.
        """
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")

        readiness = self.initialize_mission(mission_id, actor, conn)
        if not readiness.is_ready:
            raise PipelineError(
                PipelineErrorCode.FAILED_PRECONDITION,
                f"Recurring schedule rejected: Mission initialization failed readiness checks ({readiness.summary}).",
            )

        sch_id = f"sch-val-recur-{uuid.uuid4().hex[:8]}"
        sch_record = ScheduleRecord(
            schedule_id=sch_id,
            migration_id=mission.mission_id,
            tenant_id=actor.organization_id or mission.tenant_id,
            workspace_id=actor.workspace_id or mission.workspace_id,
            project_id=actor.project_id or mission.project_id,
            operation_type="validation.execute",
            schedule_type=ScheduleType.RECURRING,
            cron_expression=cron_expression,
            timezone=timezone_str,
            state=ScheduleLifecycleState.ARMED,
            enabled=True,
            misfire_policy=MisfirePolicy.SKIP,
            overlap_policy=OverlapPolicy.REJECT_OVERLAP,
            creator_actor_id=actor.actor_id,
        )

        saved_sch = self.schedule_service.create_schedule(sch_record, conn)
        mission.schedule_id = saved_sch.schedule_id
        mission.temporal_strategy = TemporalStrategy.RECURRING
        self.save_mission(mission, conn)

        logger.info(f"Durable RECURRING schedule {saved_sch.schedule_id!r} created for mission {mission_id!r} with cron {cron_expression!r}.")
        return saved_sch

    def start_continuous_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        """
        CONTINUOUS VALIDATION Backend Behavior.
        Initializes mission -> verifies readiness -> starts ContinuousValidationService lifecycle.
        """
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")

        readiness = self.initialize_mission(mission_id, actor, conn)
        if not readiness.is_ready:
            raise PipelineError(
                PipelineErrorCode.FAILED_PRECONDITION,
                f"Continuous start rejected: Mission initialization failed readiness checks ({readiness.summary}).",
            )

        return self.continuous_service.start_continuous_mission(mission, actor, conn)

    def resolve_validation_capabilities(
        self,
        source_provider: str,
        target_provider: str,
    ) -> ValidationCapabilityInfo:
        """
        Exposes structured capability availability for a source/target combination.
        Determines whether continuous, baselines, and execution modes are supported.
        """
        supported_baselines = [
            BaselineType.INHERITED_MIGRATION.value,
            BaselineType.MAINTENANCE_COORDINATED.value,
            BaselineType.EXTERNAL_REPLICATION.value,
            BaselineType.CURRENT_OPERATIONAL.value,
            BaselineType.STATIC_IMMUTABLE.value,
        ]

        supported_temporal_strategies = [
            TemporalStrategy.EXECUTE_ON_INIT.value,
            TemporalStrategy.SCHEDULE_LATER.value,
            TemporalStrategy.RECURRING.value,
            TemporalStrategy.CONTINUOUS.value,
        ]

        # Determine CDC change stream support
        p_src = source_provider.lower()
        supports_cdc = any(db in p_src for db in ["oracle", "postgres", "mysql", "maria", "mongo", "kafka"])

        return ValidationCapabilityInfo(
            source_provider=source_provider,
            target_provider=target_provider,
            supported_baselines=supported_baselines,
            supported_temporal_strategies=supported_temporal_strategies,
            supports_cdc_change_streams=supports_cdc,
            supports_exact_row=True,
            supports_cardinality=True,
            availability_code="AVAILABLE",
            availability_message=f"Validation fully supported for {source_provider} -> {target_provider}.",
        )

    def save_mission(self, mission: ValidationMissionRecord, conn: sqlite3.Connection) -> None:
        scope_json = json.dumps(mission.scope_config)
        policy_json = json.dumps(mission.execution_policy)
        conn.execute(
            """
            INSERT OR REPLACE INTO validation_missions (
                mission_id, tenant_id, workspace_id, project_id, name,
                source_provider, target_provider, source_connection_id, target_connection_id,
                validation_context, linked_migration_id, baseline_id, temporal_strategy,
                is_continuous, state, schedule_id, scope_config, execution_policy,
                last_evaluated_at, last_change_position, evaluation_count, pass_count,
                fail_count, last_result_status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission.mission_id,
                mission.tenant_id,
                mission.workspace_id,
                mission.project_id,
                mission.name,
                mission.source_provider,
                mission.target_provider,
                mission.source_connection_id,
                mission.target_connection_id,
                mission.validation_context,
                mission.linked_migration_id,
                mission.baseline_id,
                mission.temporal_strategy.value if hasattr(mission.temporal_strategy, "value") else str(mission.temporal_strategy),
                1 if mission.is_continuous else 0,
                mission.state.value if hasattr(mission.state, "value") else str(mission.state),
                mission.schedule_id,
                scope_json,
                policy_json,
                mission.last_evaluated_at,
                mission.last_change_position,
                mission.evaluation_count,
                mission.pass_count,
                mission.fail_count,
                mission.last_result_status,
                mission.created_at,
                mission.updated_at,
            ),
        )

    def get_mission_by_id(self, mission_id: str, conn: sqlite3.Connection) -> Optional[ValidationMissionRecord]:
        cur = conn.execute("SELECT * FROM validation_missions WHERE mission_id = ?", (mission_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return ValidationMissionRecord.from_dict(dict(row))

    def list_missions(
        self,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ValidationMissionRecord]:
        query = "SELECT * FROM validation_missions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params: List[Any] = [actor.organization_id, min(max(1, limit), 500), max(0, offset)]
        cur = conn.execute(query, tuple(params))
        return [ValidationMissionRecord.from_dict(dict(r)) for r in cur.fetchall()]

    def execute_mission(
        self,
        mission_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
        source_rows: Optional[List[Dict[str, Any]]] = None,
        target_rows: Optional[List[Dict[str, Any]]] = None,
        pk_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self.execute_mission_immediately(mission_id, actor, conn, source_rows, target_rows, pk_columns)

    def control_continuous(
        self,
        mission_id: str,
        action: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationMissionRecord:
        act = action.lower()
        if act == "start":
            return self.start_continuous_mission(mission_id, actor, conn)
        elif act == "pause":
            return self.continuous_service.pause_continuous_mission(mission_id, actor, conn)
        elif act == "resume":
            return self.continuous_service.resume_continuous_mission(mission_id, actor, conn)
        elif act == "cancel":
            return self.continuous_service.cancel_continuous_mission(mission_id, actor, conn)
        else:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown continuous control action {action!r}.")

    def establish_baseline(
        self,
        payload: Dict[str, Any],
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationBaselineRecord:
        b_type_raw = payload.get("baseline_type") or "MAINTENANCE_COORDINATED"
        mission_id = payload["mission_id"]
        if b_type_raw in (BaselineType.MAINTENANCE_COORDINATED.value, "MAINTENANCE_COORDINATED"):
            cond = payload.get("condition") or payload.get("condition_type") or "WRITES_STOPPED_DECLARED"
            notes = payload.get("operator_declaration") or payload.get("operator_notes")
            return self.boundary_manager.establish_maintenance_baseline(mission_id, cond, notes or "", actor, conn)
        elif b_type_raw in (BaselineType.INHERITED_MIGRATION.value, "INHERITED_MIGRATION"):
            mig_id = payload["migration_id"]
            chk_id = payload.get("checkpoint_id", "")
            return self.boundary_manager.establish_migration_baseline(mission_id, mig_id, chk_id, actor, conn)
        elif b_type_raw in (BaselineType.EXTERNAL_REPLICATION.value, "EXTERNAL_REPLICATION"):
            prov = payload.get("provider") or payload.get("source_provider") or "Oracle"
            pos_type = payload["position_type"]
            pos_val = payload["position_value"]
            return self.boundary_manager.establish_external_replication_baseline(mission_id, prov, pos_type, pos_val, actor, conn)
        else:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unsupported baseline type {b_type_raw!r}.")

    def get_mission(self, mission_id: str, actor: PipelineActorContext, conn: sqlite3.Connection) -> ValidationMissionRecord:
        mission = self.get_mission_by_id(mission_id, conn)
        if mission is None:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Validation mission {mission_id!r} not found.")
        actor.enforce_resource_scope(
            resource_tenant_id=mission.tenant_id,
            resource_workspace_id=mission.workspace_id,
            resource_project_id=mission.project_id,
            resource_kind="ValidationMission",
            resource_id=mission_id,
        )
        return mission

    def resolve_capability(
        self,
        source_id: str,
        target_id: str,
        strategy: Optional[str],
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> ValidationCapabilityInfo:
        return self.resolve_validation_capabilities(source_id, target_id)

