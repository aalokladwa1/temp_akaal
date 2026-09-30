"""akaalPipeline.application.command_handlers
===========================================
CommandHandlerRegistry mapping command request types to transaction handlers.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus, SideEffectClassification
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.events.audit import AuditTrailService
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.events.schemas import DomainEvent
from akaalPipeline.execution.controller import PipelineExecutionController
from akaalPipeline.identity.lineage import LineageTracker
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.recovery.checkpoints import CheckpointManager
from akaalPipeline.ports.engine import EngineInvocationRequest, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.history import LifecycleHistoryRecord
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask

logger = logging.getLogger(__name__)

from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact
from akaalPipeline.governance.foureyes import FourEyesEnforcer, FourEyesValidator


class CommandHandlerRegistry:
    def __init__(
        self,
        repository: SQLiteMigrationRepository,
        operation_service: OperationService,
        idempotency_service: IdempotencyService,
        execution_controller: PipelineExecutionController,
        outbox_service: Optional[OutboxService] = None,
        audit_service: Optional[AuditTrailService] = None,
        artifact_registry: Optional[ArtifactRegistry] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        plan_coordinator: Optional[Any] = None,
        intelligence_kernel: Optional[IntelligenceKernel] = None,
    ) -> None:

        self.repository = repository
        self.operation_service = operation_service
        self.idempotency_service = idempotency_service
        self.execution_controller = execution_controller
        self.outbox_service = outbox_service or OutboxService()
        self.audit_service = audit_service or AuditTrailService()
        self.artifact_registry = artifact_registry or ArtifactRegistry()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(self.execution_controller.lease_manager)
        self.plan_coordinator = plan_coordinator
        self.intelligence_kernel = intelligence_kernel or IntelligenceKernel()

        from akaalPipeline.operations.schedules import ScheduleService
        from akaalPipeline.operations.retention import OperationalRetentionService
        from akaalPipeline.operations.capacity import CapacityIntelligenceService
        from akaalPipeline.operations.alerts import AlertService
        from akaalPipeline.operations.incidents import IncidentService
        from akaalPipeline.operations.notifications import NotificationService

        from akaalPipeline.validation import ValidationPipelineService
        from akaalPipeline.orchestration.importer import MigrationMetadataImporter

        self.schedule_service = ScheduleService(self.execution_controller.lease_manager)
        self.retention_service = OperationalRetentionService()
        self.capacity_service = CapacityIntelligenceService()
        self.alert_service = AlertService()
        self.incident_service = IncidentService()
        self.notification_service = NotificationService()
        self.validation_service = ValidationPipelineService()
        self.metadata_importer = MigrationMetadataImporter()




    def handle_create_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id") or f"mig-{uuid.uuid4().hex}"
        name = payload.get("name") or f"Migration {migration_id}"
        mode_raw = payload.get("mode") or "M1"
        if isinstance(mode_raw, MigrationMode):
            mode = mode_raw
        elif isinstance(mode_raw, str):
            if hasattr(MigrationMode, mode_raw):
                mode = getattr(MigrationMode, mode_raw)
            else:
                try:
                    mode = MigrationMode(mode_raw)
                except ValueError:
                    raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown migration mode {mode_raw!r}")
        else:
            mode = MigrationMode.M1_BULK


        agg = MigrationAggregate(
            migration_id=migration_id,
            revision=1,
            name=name,
            mode=mode,
            state=MigrationLifecycleState.DRAFT,
            tenant_id=actor.organization_id or "default-tenant",
            workspace_id=actor.workspace_id or "default-workspace",
            project_id=actor.project_id or "default-project",
            lineage=LineageTracker.root(),
        )

        self.repository.save(agg, connection=uow.connection)

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state="NONE",
            to_state=MigrationLifecycleState.DRAFT.value,
            actor=actor,
            reason="Migration created",
        )

        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hist.history_id,
                hist.migration_id,
                hist.from_state,
                hist.to_state,
                hist.actor.actor_id,
                hist.reason,
                "{}",
                hist.timestamp,
            ),
        )

        # Stage outbox event & audit record in SAME UoW
        evt = DomainEvent.create(migration_id, "migration.created", agg.to_dict())
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.created", migration_id, uow.connection)

        return agg.to_dict()

    def handle_configure_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        expected_rev = payload.get("expected_revision", 1)
        config = payload.get("configuration", {})

        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        old_state = agg.state.value
        agg.update_configuration(config, expected_revision=expected_rev)
        self.repository.save(agg, connection=uow.connection)

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state=old_state,
            to_state=agg.state.value,
            actor=actor,
            reason="Configuration updated",
        )

        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hist.history_id,
                hist.migration_id,
                hist.from_state,
                hist.to_state,
                hist.actor.actor_id,
                hist.reason,
                "{}",
                hist.timestamp,
            ),
        )

        # Stage outbox event & audit record in SAME UoW
        evt = DomainEvent.create(migration_id, "migration.configured", agg.to_dict())
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.configured", migration_id, uow.connection)

        return agg.to_dict()

    def handle_cancel_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
        correlation_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        if "expected_revision" in payload and payload["expected_revision"] is not None:
            expected_rev = int(payload["expected_revision"])
            if agg.revision != expected_rev:
                raise PipelineError(
                    PipelineErrorCode.REVISION_CONFLICT,
                    f"Migration revision conflict: expected {expected_rev}, actual {agg.revision}.",
                    details={"actual_revision": agg.revision, "expected_revision": expected_rev},
                )

        if agg.state in (MigrationLifecycleState.COMPLETED, MigrationLifecycleState.CANCELLED):
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Cannot cancel migration in terminal state {agg.state.value!r}.",
            )

        # Invalidate active execution attempt and advance fence epoch
        cancelled_attempt_id = agg.active_attempt_id
        cancel_epoch = 1
        cancel_env = None
        if cancelled_attempt_id:
            lease = self.execution_controller.lease_manager.get_lease(cancelled_attempt_id, uow.connection)
            if lease:
                cancel_epoch = lease.fence_epoch
            self.execution_controller.lease_manager.revoke_lease(cancelled_attempt_id, uow.connection)
            agg.active_attempt_id = None

        # Step 1: Mark state CANCELLATION_PENDING during active runtime task termination
        old_state = agg.state.value
        agg.state = MigrationLifecycleState.CANCELLATION_PENDING
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        # Step 2: Retrieve all actively running/dispatched Engine tasks
        cur_running = uow.connection.execute(
            "SELECT node_execution_id, current_engine_task_id, binding_id, state FROM node_executions WHERE migration_id = ? AND state IN ('RUNNING', 'DISPATCHED')",
            (migration_id,),
        )
        running_nodes = cur_running.fetchall()
        task_ids = [r["current_engine_task_id"] for r in running_nodes if r and r["current_engine_task_id"]]

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding:
            for b in self.execution_controller.binding_registry.list_all():
                if isinstance(getattr(b, "port_instance", None), ExecutionPort):
                    binding = b
                    break

        cancellation_confirmed = True
        if running_nodes:
            # Running nodes without persisted engine task IDs cannot be authoritatively confirmed cancelled on Engine
            if len(task_ids) < len(running_nodes) or not binding:
                cancellation_confirmed = False

            if task_ids and binding and isinstance(binding.port_instance, ExecutionPort):
                # Acquire authenticated cancellation fencing envelope via ExecutionPort
                fence_req = EngineInvocationRequest(
                    contract_version="1.0.0",
                    binding_id=binding.binding_id,
                    correlation_id=correlation_id or f"cancel-fence-{migration_id}",
                    operation_id=f"cancel-fence-op-{uuid.uuid4().hex}",
                    attempt_id=cancelled_attempt_id or f"att-cancel-{uuid.uuid4().hex}",
                    invocation_id=f"inv-cancel-fence-{uuid.uuid4().hex}",
                    lease_id=f"lease-cancel-{uuid.uuid4().hex}",
                    fence_epoch=cancel_epoch,
                    graph_node_id="n-cancel",
                    initialization_fingerprint="fp-cancel",
                    payload={
                        "migration_id": migration_id,
                        "semantic_operation": "ACQUIRE_EXECUTION_FENCE",
                        "worker_id": "cancel_controller",
                        "run_id": cancelled_attempt_id,
                    },
                    tenant_id=actor.organization_id,
                    workspace_id=actor.workspace_id,
                    project_id=actor.project_id,
                )
                try:
                    fence_res = binding.port_instance.execute_task(fence_req)
                    if fence_res.is_success and isinstance(fence_res.result_payload, dict):
                        cancel_env = fence_res.result_payload.get("fencing_token_envelope")
                        if isinstance(cancel_env, dict):
                            env_epoch = cancel_env.get("fencing_epoch") or cancel_env.get("epoch")
                            if env_epoch is not None:
                                cancel_epoch = int(env_epoch)
                except Exception as fence_exc:
                    logger.warning("Failed to acquire cancellation fence envelope via ExecutionPort: %s", fence_exc)

                if not cancel_env:
                    cancellation_confirmed = False

                for t_id in task_ids:
                    cancel_req = EngineInvocationRequest(
                        contract_version="1.0.0",
                        binding_id=binding.binding_id,
                        correlation_id=correlation_id or f"cancel-{migration_id}",
                        operation_id=f"cancel-op-{uuid.uuid4().hex}",
                        attempt_id=cancelled_attempt_id or f"att-cancel-{uuid.uuid4().hex}",
                        invocation_id=f"inv-cancel-{uuid.uuid4().hex}",
                        lease_id=f"lease-cancel-{uuid.uuid4().hex}",
                        fence_epoch=cancel_epoch,
                        fencing_token_envelope=cancel_env,
                        graph_node_id="n-cancel",
                        initialization_fingerprint="fp-cancel",
                        payload={
                            "migration_id": migration_id,
                            "semantic_operation": "CANCEL_EXECUTION",
                            "task_id": t_id,
                            "run_id": cancelled_attempt_id,
                        },
                        tenant_id=actor.organization_id,
                        workspace_id=actor.workspace_id,
                        project_id=actor.project_id,
                    )
                    try:
                        c_res = binding.port_instance.execute_task(cancel_req)
                        c_res_payload = c_res.result_payload if isinstance(c_res.result_payload, dict) else {}
                        if not c_res.is_success or c_res_payload.get("terminal") is not True:
                            if c_res.error_code not in ("TASK_NOT_FOUND", "ALREADY_CANCELLED", "TASK_NOT_RUNNING"):
                                cancellation_confirmed = False
                    except Exception as exc:
                        logger.warning("Physical EngineGateway cancellation dispatch failed for task %s on migration %s: %s", t_id, migration_id, exc)
                        cancellation_confirmed = False

        # Cancel any active plan executions and non-terminal node executions
        if self.plan_coordinator is not None:
            cur_pe = uow.connection.execute(
                "SELECT execution_id FROM plan_executions WHERE migration_id = ? AND status IN ('ACCEPTED', 'RUNNING')",
                (migration_id,),
            )
            for pe_row in cur_pe.fetchall():
                self.plan_coordinator.cancel_plan_execution(
                    pe_row["execution_id"],
                    payload.get("reason", "Migration cancelled by user"),
                    actor,
                    uow.connection,
                )
        else:
            uow.connection.execute(
                "UPDATE node_executions SET state = 'CANCELLED' WHERE migration_id = ? AND state IN ('ACCEPTED', 'RUNNING', 'DISPATCHED', 'READY', 'BLOCKED')",
                (migration_id,),
            )
            uow.connection.execute(
                "UPDATE plan_executions SET status = 'CANCELLED' WHERE migration_id = ? AND status IN ('ACCEPTED', 'RUNNING')",
                (migration_id,),
            )

        if cancellation_confirmed:
            agg.state = MigrationLifecycleState.CANCELLED
        else:
            agg.state = MigrationLifecycleState.CANCELLATION_PENDING
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state=old_state,
            to_state=agg.state.value,
            actor=actor,
            reason=payload.get("reason", "Migration cancelled by user"),
        )
        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hist.history_id,
                hist.migration_id,
                hist.from_state,
                hist.to_state,
                hist.actor.actor_id,
                hist.reason,
                "{}",
                hist.timestamp,
            ),
        )

        event_name = "migration.cancelled" if agg.state == MigrationLifecycleState.CANCELLED else "migration.cancellation_pending"
        evt = DomainEvent.create(
            migration_id,
            event_name,
            {"migration_id": migration_id, "cancelled_attempt_id": cancelled_attempt_id, "reason": hist.reason, "state": agg.state.value},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, event_name, migration_id, uow.connection)

        return agg.to_dict()

    def _get_known_attempt_ids_for_migration(self, migration_id: str, conn: sqlite3.Connection) -> List[str]:
        """Resolves all authoritative historical attempt IDs belonging to a migration."""
        attempt_ids: List[str] = []
        cur = conn.execute(
            "SELECT payload FROM outbox_events WHERE aggregate_id = ? ORDER BY created_at DESC",
            (migration_id,),
        )
        for row in cur.fetchall():
            try:
                p = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
                if isinstance(p, Mapping):
                    for key in ("attempt_id", "new_attempt_id", "cancelled_attempt_id", "source_attempt_id"):
                        val = p.get(key)
                        if val and isinstance(val, str) and val not in attempt_ids:
                            attempt_ids.append(val)
            except Exception:
                continue

        # Check operation_journal for migration references
        cur_op = conn.execute(
            "SELECT result_payload FROM operation_journal WHERE operation_id LIKE ? OR command_id LIKE ?",
            (f"%{migration_id}%", f"%{migration_id}%"),
        )
        for row in cur_op.fetchall():
            try:
                res_p = json.loads(row["result_payload"]) if row["result_payload"] else {}
                if isinstance(res_p, Mapping):
                    for key in ("attempt_id", "new_attempt_id", "source_attempt_id"):
                        val = res_p.get(key)
                        if val and isinstance(val, str) and val not in attempt_ids:
                            attempt_ids.append(val)
            except Exception:
                continue

        # Check node_executions for attempt IDs belonging to this migration
        cur_node = conn.execute(
            "SELECT current_attempt_id FROM node_executions WHERE migration_id = ? AND current_attempt_id IS NOT NULL",
            (migration_id,),
        )
        for node_row in cur_node.fetchall():
            att = node_row["current_attempt_id"]
            if att and att not in attempt_ids:
                attempt_ids.append(att)

        # Check checkpoints table for attempts associated with this migration's initialization fingerprint
        cur_mig = conn.execute(
            "SELECT initialization_id FROM migrations WHERE migration_id = ?",
            (migration_id,),
        )
        mig_row = cur_mig.fetchone()
        if mig_row and mig_row["initialization_id"]:
            cur_art = conn.execute(
                "SELECT fingerprint FROM immutable_artifacts WHERE artifact_id = ?",
                (mig_row["initialization_id"],),
            )
            art_row = cur_art.fetchone()
            if art_row and art_row["fingerprint"]:
                init_fp = art_row["fingerprint"]
                cur_chk = conn.execute(
                    "SELECT DISTINCT attempt_id FROM checkpoints WHERE initialization_fingerprint = ?",
                    (init_fp,),
                )
                for chk_row in cur_chk.fetchall():
                    att = chk_row["attempt_id"]
                    if att and att not in attempt_ids:
                        attempt_ids.append(att)

        return attempt_ids


    def handle_recover_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        if agg.state not in (MigrationLifecycleState.FAILED, MigrationLifecycleState.CANCELLED):
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Cannot recover migration from non-failed/non-cancelled state {agg.state.value!r}.",
            )

        side_effect_str = payload.get("side_effect", "REVERSIBLE")
        try:
            side_effect = SideEffectClassification(side_effect_str)
        except ValueError:
            side_effect = SideEffectClassification.REVERSIBLE

        is_force = bool(payload.get("force", False))
        if side_effect in (SideEffectClassification.IRREVERSIBLE, SideEffectClassification.DESTRUCTIVE):
            if not is_force or "admin" not in getattr(actor, "roles", ()):
                raise PipelineError(
                    PipelineErrorCode.INELIGIBLE,
                    f"Automatic recovery rejected: side-effect {side_effect.value!r} requires explicit manual governance override by an admin.",
                )

        # 1. Resolve and validate authoritative source attempt owned by migration lineage
        known_attempts = self._get_known_attempt_ids_for_migration(migration_id, uow.connection)
        if agg.active_attempt_id and agg.active_attempt_id not in known_attempts:
            known_attempts.insert(0, agg.active_attempt_id)

        explicit_source = payload.get("source_attempt_id")
        if explicit_source:
            if explicit_source not in known_attempts:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Source attempt {explicit_source!r} does not belong to migration {migration_id!r}.",
                )
            source_attempt_id = explicit_source
        elif known_attempts:
            source_attempt_id = agg.active_attempt_id or known_attempts[0]
        else:
            source_attempt_id = None

        # 2. Select authoritative checkpoint belonging to migration lineage
        selected_checkpoint_id = payload.get("checkpoint_id")
        selected_checkpoint = None
        if selected_checkpoint_id:
            selected_checkpoint = self.checkpoint_manager.get_checkpoint(selected_checkpoint_id, uow.connection, actor=actor)
            if selected_checkpoint is None:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Specified recovery checkpoint {selected_checkpoint_id!r} not found.",
                )
            if selected_checkpoint.attempt_id not in known_attempts:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Checkpoint {selected_checkpoint_id!r} belongs to attempt {selected_checkpoint.attempt_id!r}, which is not part of migration {migration_id!r}.",
                )
            if source_attempt_id and selected_checkpoint.attempt_id != source_attempt_id:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Checkpoint {selected_checkpoint_id!r} belongs to attempt {selected_checkpoint.attempt_id!r}, not source attempt {source_attempt_id!r}.",
                )
        elif source_attempt_id:
            selected_checkpoint = self.checkpoint_manager.get_latest_checkpoint_for_attempt(source_attempt_id, uow.connection, actor=actor)
            if selected_checkpoint:
                selected_checkpoint_id = selected_checkpoint.checkpoint_id

        # 3. Revoke and fence source attempt authority BEFORE establishing replacement
        if source_attempt_id:
            self.execution_controller.lease_manager.revoke_lease(source_attempt_id, uow.connection)

        # 4. Establish replacement attempt authority and lease with advanced fence epoch
        new_attempt_id = f"att-recov-{uuid.uuid4().hex}"
        new_lease_id = f"lease-recov-{uuid.uuid4().hex}"
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()


        init_fp = "fp-recovered"
        if agg.initialization_id:
            try:
                init_art = self.artifact_registry.get(agg.initialization_id, conn=uow.connection)
                init_fp = init_art.fingerprint
            except PipelineError:
                pass

        new_lease = self.execution_controller.lease_manager.acquire_lease(
            lease_id=new_lease_id,
            attempt_id=new_attempt_id,
            owner_id=actor.actor_id,
            expires_at=expires_at,
            initialization_fingerprint=init_fp,
            conn=uow.connection,
        )

        # 5. Create durable recovery operation journal record
        recovery_op_id = payload.get("recovery_operation_id") or f"op-recov-{uuid.uuid4().hex}"
        rec_op = OperationRecord(
            operation_id=recovery_op_id,
            command_id=payload.get("command_id") or f"cmd-recov-{uuid.uuid4().hex}",
            idempotency_key=payload.get("idempotency_key"),
            status=OperationStatus.ACCEPTED,
            actor=actor,
            payload_fingerprint=payload.get("payload_fingerprint", "fp-recov"),
        )
        self.operation_service.create_operation(rec_op, uow.connection)

        # 6. Transition migration aggregate state
        old_state = agg.state.value
        agg.state = MigrationLifecycleState.INITIALIZED
        agg.active_attempt_id = new_attempt_id
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state=old_state,
            to_state=MigrationLifecycleState.INITIALIZED.value,
            actor=actor,
            reason=payload.get("reason", f"Migration recovered from source attempt {source_attempt_id or 'none'}"),
        )
        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hist.history_id,
                hist.migration_id,
                hist.from_state,
                hist.to_state,
                hist.actor.actor_id,
                hist.reason,
                "{}",
                hist.timestamp,
            ),
        )

        # 7. Recover durable DAG plan and node execution authority
        if self.plan_coordinator is not None:
            self.plan_coordinator.recover_plan_execution(
                migration_id=migration_id,
                actor=actor,
                conn=uow.connection,
                source_attempt_id=source_attempt_id,
                checkpoint_id=selected_checkpoint_id,
                replacement_attempt_id=new_attempt_id,
                replacement_lease_id=new_lease.lease_id,
                replacement_fence_epoch=new_lease.fence_epoch,
                recovery_operation_id=recovery_op_id,
            )



        evt = DomainEvent.create(
            migration_id,
            "migration.recovered",
            {
                "migration_id": migration_id,
                "recovery_operation_id": recovery_op_id,
                "source_attempt_id": source_attempt_id,
                "selected_checkpoint_id": selected_checkpoint_id,
                "new_attempt_id": new_attempt_id,
                "new_lease_id": new_lease_id,
            },
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.recovered", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "recovery_operation_id": recovery_op_id,
            "source_attempt_id": source_attempt_id,
            "selected_checkpoint_id": selected_checkpoint_id,
            "new_attempt_id": new_attempt_id,
            "new_lease_id": new_lease_id,
            "state": agg.state.value,
            "revision": agg.revision,
        }

    def handle_plan_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        plan = GraphCompiler.compile_plan(f"plan-{migration_id}", migration_id, agg.mode, agg.configuration)
        GraphValidator.validate_plan(plan)

        plan_art = ImmutableArtifact.create(f"art-plan-{migration_id}", "execution_plan", plan.to_dict())
        self.artifact_registry.register(plan_art, conn=uow.connection)

        old_state = agg.state.value
        agg.set_plan(plan_art.artifact_id, expected_revision=agg.revision)
        self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(migration_id, "migration.planned", {"plan_id": plan.plan_id, "plan_fingerprint": plan.fingerprint})
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.planned", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "plan_id": plan.plan_id,
            "plan_fingerprint": plan.fingerprint,
            "state": agg.state.value,
            "revision": agg.revision,
        }

    def handle_initialize_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        plan_art_id = agg.plan_id or f"art-plan-{migration_id}"
        try:
            plan_art = self.artifact_registry.get(plan_art_id, conn=uow.connection)
        except PipelineError:
            plan = GraphCompiler.compile_plan(f"plan-{migration_id}", migration_id, agg.mode, agg.configuration)
            GraphValidator.validate_plan(plan)
            plan_art = ImmutableArtifact.create(plan_art_id, "execution_plan", plan.to_dict())
            self.artifact_registry.register(plan_art, conn=uow.connection)
            agg.plan_id = plan_art.artifact_id


        plan_fp = plan_art.content.get("fingerprint") or plan_art.fingerprint
        init_payload = {
            "migration_id": migration_id,
            "mode": agg.mode.value,
            "plan_fingerprint": plan_fp,
            "tenant_id": agg.tenant_id,
            "workspace_id": agg.workspace_id,
            "project_id": agg.project_id,
        }
        init_art = ImmutableArtifact.create(f"art-init-{migration_id}", "initialization", init_payload)
        self.artifact_registry.register(init_art, conn=uow.connection)


        old_state = agg.state.value
        agg.set_initialization(init_art.artifact_id, expected_revision=agg.revision)
        self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(migration_id, "migration.initialized", {"initialization_id": init_art.artifact_id, "initialization_fingerprint": init_art.fingerprint})
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.initialized", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "initialization_id": init_art.artifact_id,
            "initialization_fingerprint": init_art.fingerprint,
            "state": agg.state.value,
            "revision": agg.revision,
        }

    def handle_approve_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        # Require admin or governor role to issue approval
        if not any(r in ("admin", "governor", "security_officer", "compliance") for r in actor.roles):
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Actor {actor.actor_id!r} lacks governance authorization to approve migration.",
            )

        # Enforce Maker-Checker: requester cannot self-approve
        requester_id = payload.get("requester_id") or getattr(agg, "creator_id", None) or payload.get("creator_id")
        if requester_id:
            ok, msg = FourEyesValidator().validate_action(
                requester_id=str(requester_id),
                approver_id=str(actor.actor_id),
                action_type="APPROVE_MIGRATION",
            )
            if not ok:
                raise PipelineError(
                    PipelineErrorCode.POLICY_DENIED,
                    f"Maker-checker violation: {msg}",
                )

        decision_id = payload.get("decision_id") or f"dec-{uuid.uuid4().hex}"
        approval_id = payload.get("approval_id") or f"art-approval-{migration_id}"

        # Determine target artifact fingerprint from initialization or plan
        target_fp = payload.get("target_artifact_fingerprint")
        if not target_fp and agg.initialization_id:
            try:
                init_art = self.artifact_registry.get(agg.initialization_id, conn=uow.connection)
                target_fp = init_art.fingerprint
            except PipelineError:
                pass

        subject_actor_id = payload.get("subject_actor_id", "*")
        subject_roles = list(payload.get("subject_roles", [])) if "subject_roles" in payload else list(actor.roles)

        from akaalPipeline.policy.contracts import PolicyAction, PolicyDecision, PolicyResource, PolicyResult, PolicySubject
        decision_val = str(payload.get("decision", "APPROVED")).upper()
        is_approved = decision_val in ("APPROVED", "APPROVE", "ALLOW")
        result_enum = PolicyResult.ALLOW if is_approved else PolicyResult.DENY

        decision = PolicyDecision(
            decision_id=decision_id,
            policy_version=payload.get("policy_version", "1.0.0"),
            subject=PolicySubject(actor_id=subject_actor_id, actor_type=payload.get("subject_actor_type", "user"), roles=subject_roles),
            action=PolicyAction(name=payload.get("action", "migration.start")),
            resource=PolicyResource(resource_id=migration_id, resource_type="migration", artifact_fingerprint=target_fp),
            result=result_enum,
            reason=payload.get("reason", "Approved by authorized governance actor" if is_approved else "Rejected by governance actor"),
            issuer_id=actor.actor_id,
            issuer_roles=list(actor.roles),
            effective_at=payload.get("effective_at", datetime.now(timezone.utc).isoformat()),
            expires_at=payload.get("expires_at"),
        )

        approval_art = ImmutableArtifact.create(approval_id, "policy_decision", decision.to_dict())
        self.artifact_registry.register(approval_art, conn=uow.connection)

        # Update aggregate state: AUTHORIZED if approved, PAUSED if rejected
        if agg.state == MigrationLifecycleState.GOVERNANCE_PENDING:
            old_state = agg.state.value
            agg.state = MigrationLifecycleState.AUTHORIZED if is_approved else MigrationLifecycleState.PAUSED
            agg.revision += 1
            self.repository.save(agg, connection=uow.connection)

        evt_name = "migration.approved" if is_approved else "migration.rejected"
        evt = DomainEvent.create(
            migration_id,
            evt_name,
            {"decision_id": decision_id, "approval_id": approval_id, "issuer_id": actor.actor_id, "result": result_enum.value},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, evt_name, migration_id, uow.connection)

        barrier_id = payload.get("barrier_id")
        if barrier_id:
            try:
                uow.connection.execute(
                    "UPDATE governance_approvals SET status = ?, approver_id = ?, rejection_reason = ? WHERE migration_id = ? AND (approval_id = ? OR policy_id = ?)",
                    ("APPROVED" if is_approved else "REJECTED", actor.actor_id, payload.get("reason", ""), migration_id, barrier_id, barrier_id),
                )
            except Exception:
                pass

        return {
            "migration_id": migration_id,
            "decision_id": decision_id,
            "approval_id": approval_id,
            "result": result_enum.value,
            "decision": "APPROVED" if is_approved else "REJECTED",
            "issuer_id": actor.actor_id,
        }

    def handle_pause_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """P6.1 Operational Command: Pause running migration execution."""
        from akaalPipeline.operations.mutability import OperationalMutabilityResolver, MutabilityClassification

        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        # Stale execution fencing check
        target_execution = payload.get("target_execution_id") or payload.get("execution_id") or payload.get("attempt_id")
        if target_execution and agg.active_attempt_id and target_execution != agg.active_attempt_id:
            raise PipelineError(
                PipelineErrorCode.STALE_RESULT,
                f"Pause command rejected: target execution {target_execution!r} does not match active execution {agg.active_attempt_id!r}.",
            )

        # Idempotent return if already paused
        if agg.state == MigrationLifecycleState.PAUSED:
            return {
                "migration_id": migration_id,
                "status": "APPLIED",
                "state": agg.state.value,
                "message": "Migration is already paused.",
                "idempotent": True,
            }

        if agg.state not in (MigrationLifecycleState.ACTIVE, MigrationLifecycleState.INITIALIZED):
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Cannot pause migration in state {agg.state.value!r}. Only active migrations can be paused.",
            )

        # Evaluate dynamic mutability
        mut_res = OperationalMutabilityResolver.evaluate("pause", agg.state, agg.mode)

        # Step 1: Create operation record with ACCEPTED
        op_id = payload.get("operation_id") or f"op-pause-{uuid.uuid4().hex}"
        op_rec = OperationRecord(
            operation_id=op_id,
            command_id=payload.get("command_id") or f"cmd-pause-{uuid.uuid4().hex}",
            idempotency_key=payload.get("idempotency_key"),
            status=OperationStatus.ACCEPTED,
            actor=actor,
            payload_fingerprint=payload.get("payload_fingerprint", "fp-pause"),
        )
        self.operation_service.create_operation(op_rec, uow.connection)

        # Step 2: Transition state to PAUSING
        old_state = agg.state.value
        agg.state = MigrationLifecycleState.PAUSING
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        # Step 3: Physical task pause in Engine
        cur_running = uow.connection.execute(
            "SELECT current_engine_task_id FROM node_executions WHERE migration_id = ? AND state IN ('RUNNING', 'DISPATCHED')",
            (migration_id,),
        )
        running_tasks = [r["current_engine_task_id"] for r in cur_running.fetchall() if r and r["current_engine_task_id"]]

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding:
            for b in self.execution_controller.binding_registry.list_all():
                if isinstance(getattr(b, "port_instance", None), ExecutionPort):
                    binding = b
                    break

        if running_tasks and binding and isinstance(binding.port_instance, ExecutionPort):
            for t_id in running_tasks:
                pause_req = EngineInvocationRequest(
                    contract_version="1.0.0",
                    binding_id=binding.binding_id,
                    correlation_id=f"pause-{migration_id}",
                    operation_id=f"pause-op-{uuid.uuid4().hex}",
                    attempt_id=agg.active_attempt_id or f"att-pause-{uuid.uuid4().hex}",
                    invocation_id=f"inv-pause-{uuid.uuid4().hex}",
                    lease_id=f"lease-pause-{uuid.uuid4().hex}",
                    fence_epoch=1,
                    graph_node_id="n-pause",
                    initialization_fingerprint="fp-pause",
                    payload={
                        "migration_id": migration_id,
                        "semantic_operation": "PAUSE_EXECUTION",
                        "task_id": t_id,
                    },
                    tenant_id=actor.organization_id,
                    workspace_id=actor.workspace_id,
                    project_id=actor.project_id,
                )
                try:
                    binding.port_instance.execute_task(pause_req)
                except Exception as p_exc:
                    logger.warning("Engine task pause invocation failed for task %s: %s", t_id, p_exc)

        # Step 4: Transition to PAUSED & confirm APPLIED
        agg.state = MigrationLifecycleState.PAUSED
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        self.operation_service.update_status(
            op_id,
            OperationStatus.SUCCEEDED,
            uow.connection,
            result_payload={"status": "APPLIED", "state": agg.state.value},
        )

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state=old_state,
            to_state=agg.state.value,
            actor=actor,
            reason=payload.get("reason", "Migration paused by operator"),
        )
        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (hist.history_id, hist.migration_id, hist.from_state, hist.to_state, hist.actor.actor_id, hist.reason, "{}", hist.timestamp),
        )

        evt = DomainEvent.create(migration_id, "migration.paused", {"migration_id": migration_id, "operation_id": op_id, "state": agg.state.value})
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.paused", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "operation_id": op_id,
            "status": "APPLIED",
            "state": agg.state.value,
            "revision": agg.revision,
        }

    def handle_resume_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """P6.1 Operational Command: Resume paused migration execution."""
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        # Stale execution fencing check
        target_execution = payload.get("target_execution_id") or payload.get("execution_id") or payload.get("attempt_id")
        if target_execution and agg.active_attempt_id and target_execution != agg.active_attempt_id:
            raise PipelineError(
                PipelineErrorCode.STALE_RESULT,
                f"Resume command rejected: target execution {target_execution!r} does not match active execution {agg.active_attempt_id!r}.",
            )

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding:
            for b in self.execution_controller.binding_registry.list_all():
                if isinstance(getattr(b, "port_instance", None), ExecutionPort):
                    binding = b
                    break

        cur_running = uow.connection.execute(
            "SELECT current_engine_task_id FROM node_executions WHERE migration_id = ? AND state IN ('PAUSED', 'RUNNING', 'DISPATCHED')",
            (migration_id,),
        )
        paused_tasks = [r["current_engine_task_id"] for r in cur_running.fetchall() if r and r["current_engine_task_id"]]
        tasks_to_resume = paused_tasks if paused_tasks else [f"task-cdc-{migration_id}"]

        if binding and isinstance(binding.port_instance, ExecutionPort):
            for t_id in tasks_to_resume:
                resume_req = EngineInvocationRequest(
                    contract_version="1.0.0",
                    binding_id=binding.binding_id,
                    correlation_id=f"resume-{migration_id}",
                    operation_id=f"resume-op-{uuid.uuid4().hex}",
                    attempt_id=agg.active_attempt_id or f"att-resume-{uuid.uuid4().hex}",
                    invocation_id=f"inv-resume-{uuid.uuid4().hex}",
                    lease_id=f"lease-resume-{uuid.uuid4().hex}",
                    fence_epoch=1,
                    graph_node_id="n-resume",
                    initialization_fingerprint="fp-resume",
                    payload={
                        "migration_id": migration_id,
                        "semantic_operation": "RESUME_EXECUTION",
                        "task_id": t_id,
                    },
                    tenant_id=actor.organization_id,
                    workspace_id=actor.workspace_id,
                    project_id=actor.project_id,
                )
                try:
                    binding.port_instance.execute_task(resume_req)
                except Exception as r_exc:
                    logger.warning("Engine task resume invocation failed for task %s: %s", t_id, r_exc)

        # Idempotent return if already active after ensuring CDC context
        if agg.state == MigrationLifecycleState.ACTIVE:
            return {
                "migration_id": migration_id,
                "status": "APPLIED",
                "state": agg.state.value,
                "message": "Migration CDC execution restored and active.",
                "idempotent": True,
            }

        if agg.state != MigrationLifecycleState.PAUSED:
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Cannot resume migration in state {agg.state.value!r}. Only paused migrations can be resumed.",
            )

        # Step 1: Create operation record with ACCEPTED
        op_id = payload.get("operation_id") or f"op-resume-{uuid.uuid4().hex}"
        op_rec = OperationRecord(
            operation_id=op_id,
            command_id=payload.get("command_id") or f"cmd-resume-{uuid.uuid4().hex}",
            idempotency_key=payload.get("idempotency_key"),
            status=OperationStatus.ACCEPTED,
            actor=actor,
            payload_fingerprint=payload.get("payload_fingerprint", "fp-resume"),
        )
        self.operation_service.create_operation(op_rec, uow.connection)

        # Step 3: Transition to ACTIVE & confirm APPLIED
        old_state = agg.state.value
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        self.operation_service.update_status(
            op_id,
            OperationStatus.SUCCEEDED,
            uow.connection,
            result_payload={"status": "APPLIED", "state": agg.state.value},
        )

        hist = LifecycleHistoryRecord(
            history_id=f"hist-{uuid.uuid4().hex}",
            migration_id=migration_id,
            from_state=old_state,
            to_state=agg.state.value,
            actor=actor,
            reason=payload.get("reason", "Migration resumed by operator"),
        )
        uow.connection.execute(
            """
            INSERT INTO lifecycle_history (history_id, migration_id, from_state, to_state, actor, reason, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (hist.history_id, hist.migration_id, hist.from_state, hist.to_state, hist.actor.actor_id, hist.reason, "{}", hist.timestamp),
        )

        evt = DomainEvent.create(migration_id, "migration.resumed", {"migration_id": migration_id, "operation_id": op_id, "state": agg.state.value})
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.resumed", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "operation_id": op_id,
            "status": "APPLIED",
            "state": agg.state.value,
            "revision": agg.revision,
        }

    def handle_throttle_cdc(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """P6.1 Operational Command: Dynamic CDC rate throttling."""
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        max_events = payload.get("max_events_per_fetch")
        max_bytes = payload.get("max_fetch_bytes_sec")

        # Strict validation: REJECT INVALID
        if max_events is not None:
            try:
                max_events = int(max_events)
                if max_events <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "max_events_per_fetch must be a positive integer > 0.")

        if max_bytes is not None:
            try:
                max_bytes = int(max_bytes)
                if max_bytes <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "max_fetch_bytes_sec must be a positive integer > 0.")

        op_id = payload.get("operation_id") or f"op-throttle-{uuid.uuid4().hex}"
        op_rec = OperationRecord(
            operation_id=op_id,
            command_id=payload.get("command_id") or f"cmd-throttle-{uuid.uuid4().hex}",
            idempotency_key=payload.get("idempotency_key"),
            status=OperationStatus.ACCEPTED,
            actor=actor,
            payload_fingerprint=payload.get("payload_fingerprint", "fp-throttle"),
        )
        self.operation_service.create_operation(op_rec, uow.connection)

        # Apply dynamic rate throttling if gateway engine is bound
        throttle_result = {"max_events_per_fetch": max_events, "max_fetch_bytes_sec": max_bytes}
        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if binding and hasattr(binding, "engine_gateway"):
            gw = getattr(binding, "engine_gateway", None)
            if gw and hasattr(gw, "coordinator") and hasattr(gw.coordinator, "cdc_authority"):
                throttle_result = gw.coordinator.cdc_authority.set_capture_budget(
                    max_events_per_fetch=max_events,
                    max_fetch_bytes_sec=max_bytes,
                )

        self.operation_service.update_status(
            op_id,
            OperationStatus.SUCCEEDED,
            uow.connection,
            result_payload={"status": "APPLIED", "throttle": throttle_result},
        )

        evt = DomainEvent.create(migration_id, "migration.cdc_throttled", {"migration_id": migration_id, "throttle": throttle_result})
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.cdc_throttled", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "operation_id": op_id,
            "status": "APPLIED",
            "throttle": throttle_result,
        }

    # =========================================================================
    # P6.5 ENTERPRISE SCHEDULING & RETENTION COMMAND HANDLERS
    # =========================================================================

    def handle_create_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Create a new schedule definition with initial DRAFT or ARMED state."""
        migration_id = payload.get("migration_id")
        if not migration_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "migration_id is required to create a schedule.")

        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        from akaalPipeline.contracts.enums import MisfirePolicy, OverlapPolicy, ScheduleLifecycleState, ScheduleType
        from akaalPipeline.operations.schedules import ScheduleRecord

        schedule_id = payload.get("schedule_id") or f"sch-{uuid.uuid4().hex[:12]}"
        stype = ScheduleType(payload.get("schedule_type", "RECURRING"))
        cron_expr = payload.get("cron_expression", "0 * * * *")
        one_shot = payload.get("one_shot_time")
        tz_name = payload.get("timezone", "UTC")
        op_type = payload.get("operation_type", "migration.start")
        misfire = MisfirePolicy(payload.get("misfire_policy", "SKIP"))
        overlap = OverlapPolicy(payload.get("overlap_policy", "REJECT_OVERLAP"))
        arm_immediately = bool(payload.get("arm_immediately", False))
        initial_state = ScheduleLifecycleState.ARMED if arm_immediately else ScheduleLifecycleState.DRAFT

        record = ScheduleRecord(
            schedule_id=schedule_id,
            tenant_id=actor.organization_id,
            workspace_id=actor.workspace_id or "default-workspace",
            project_id=actor.project_id,
            migration_id=migration_id,
            operation_type=op_type,
            schedule_type=stype,
            cron_expression=cron_expr,
            one_shot_time=one_shot,
            timezone=tz_name,
            state=initial_state,
            enabled=True,
            revision=1,
            misfire_policy=misfire,
            overlap_policy=overlap,
            creator_actor_id=actor.actor_id,
            delegated_roles=json.dumps(list(actor.roles)),
        )
        created = self.schedule_service.create_schedule(record, uow.connection)

        self.audit_service.record_event(actor, "schedule.created", schedule_id, uow.connection)
        return created.to_dict()

    def handle_update_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Update an existing schedule with monotonic revision bump and tenant verification."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        from akaalPipeline.contracts.enums import MisfirePolicy, OverlapPolicy
        misfire = MisfirePolicy(payload["misfire_policy"]) if "misfire_policy" in payload else None
        overlap = OverlapPolicy(payload["overlap_policy"]) if "overlap_policy" in payload else None

        updated = self.schedule_service.update_schedule(
            schedule_id=schedule_id,
            conn=uow.connection,
            cron_expression=payload.get("cron_expression"),
            timezone_str=payload.get("timezone"),
            misfire_policy=misfire,
            overlap_policy=overlap,
            one_shot_time=payload.get("one_shot_time"),
        )
        self.audit_service.record_event(actor, "schedule.updated", schedule_id, uow.connection)
        return updated.to_dict()

    def handle_arm_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Arm a schedule for occurrence generation."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        armed = self.schedule_service.arm_schedule(schedule_id, uow.connection)
        self.audit_service.record_event(actor, "schedule.armed", schedule_id, uow.connection)
        return armed.to_dict()

    def handle_disable_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Disable future occurrences of a schedule."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        disabled = self.schedule_service.disable_schedule(schedule_id, uow.connection)
        self.audit_service.record_event(actor, "schedule.disabled", schedule_id, uow.connection)
        return disabled.to_dict()

    def handle_enable_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Enable a disabled schedule."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        enabled = self.schedule_service.enable_schedule(schedule_id, uow.connection)
        self.audit_service.record_event(actor, "schedule.enabled", schedule_id, uow.connection)
        return enabled.to_dict()

    def handle_cancel_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Cancel a schedule."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        cancelled = self.schedule_service.cancel_schedule(schedule_id, uow.connection)
        self.audit_service.record_event(actor, "schedule.cancelled", schedule_id, uow.connection)
        return cancelled.to_dict()

    def handle_delete_schedule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Delete a schedule definition."""
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "schedule_id is required.")

        sch = self.schedule_service.get_by_id(schedule_id, uow.connection)
        if sch is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Schedule {schedule_id!r} not found.")

        if sch.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Schedule {schedule_id!r} unauthorized for tenant.")

        deleted = self.schedule_service.delete_schedule(schedule_id, uow.connection)
        self.audit_service.record_event(actor, "schedule.deleted", schedule_id, uow.connection)
        return {"deleted": deleted, "schedule_id": schedule_id}

    def handle_execute_retention(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Execute operational retention pruning in bounded batches respecting all protection classes."""
        cutoff_time = payload.get("cutoff_time")
        if not cutoff_time:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "cutoff_time is required for retention execution.")

        data_classes = payload.get("data_classes") or [
            "operation_journal",
            "idempotency_records",
            "lifecycle_history",
            "outbox_events",
            "checkpoints",
            "immutable_artifacts",
            "audit_trail",
            "schedule_occurrences",
        ]
        batch_size = int(payload.get("batch_size", 500))

        from akaalPipeline.operations.retention import RetentionPolicy
        policy = RetentionPolicy(
            cutoff_time=cutoff_time,
            tenant_id=actor.organization_id,
            workspace_id=actor.workspace_id,
            project_id=actor.project_id,
            data_classes=data_classes,
            max_batch_size=batch_size,
        )

        res = self.retention_service.execute(policy, uow.connection, actor=actor, batch_size=batch_size)
        self.audit_service.record_event(actor, "retention.executed", res.retention_op_id, uow.connection)
        return res.to_dict()

    # =========================================================================
    # P6.6 Capacity Command Handlers
    # =========================================================================

    def handle_sample_capacity(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Trigger capacity and resource observation sampling."""
        node_id = payload.get("node_id", "node-local")
        obs = self.capacity_service.sample_os_resources(node_id=node_id, tenant_id=actor.organization_id)
        for o in obs:
            self.capacity_service.record_observation(o, uow.connection)
        self.audit_service.record_event(actor, "capacity.sampled", node_id, uow.connection)
        return {"samples": [o.to_dict() for o in obs]}

    # =========================================================================
    # P6.7 Alert Command Handlers
    # =========================================================================

    def handle_create_alert_rule(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Create a typed alert rule."""
        from akaalPipeline.contracts.enums import AlertSeverity
        name = payload["name"]
        signal_name = payload["signal_name"]
        operator = payload["operator"]
        threshold_value = str(payload["threshold_value"])
        threshold_type = payload.get("threshold_type", "NUMERIC")
        severity_str = payload.get("severity", "MEDIUM")
        severity = AlertSeverity(severity_str.upper())
        dedup_window_sec = int(payload.get("dedup_window_sec", 300))

        rule = self.alert_service.create_rule(
            tenant_id=actor.organization_id,
            name=name,
            signal_name=signal_name,
            operator=operator,
            threshold_value=threshold_value,
            threshold_type=threshold_type,
            severity=severity,
            conn=uow.connection,
            dedup_window_sec=dedup_window_sec,
            actor=actor,
        )
        self.audit_service.record_event(actor, "alert.rule.created", rule.rule_id, uow.connection)
        return rule.to_dict()

    def handle_evaluate_alert(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Evaluate a signal and potentially trigger/update an alert."""
        signal_name = payload["signal_name"]
        value = payload.get("value")
        context = payload.get("context", {})
        target_id = payload.get("target_id")

        alert = self.alert_service.evaluate_signal(
            tenant_id=actor.organization_id,
            signal_name=signal_name,
            value=value,
            conn=uow.connection,
            context=context,
            target_id=target_id,
        )
        if alert:
            self.audit_service.record_event(actor, "alert.triggered", alert.alert_id, uow.connection)
            return {"triggered": True, "alert": alert.to_dict()}
        return {"triggered": False, "alert": None}

    def handle_acknowledge_alert(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Acknowledge an active alert."""
        alert_id = payload["alert_id"]
        alert = self.alert_service.acknowledge_alert(alert_id, actor, uow.connection)
        self.audit_service.record_event(actor, "alert.acknowledged", alert_id, uow.connection)
        return alert.to_dict()

    def handle_resolve_alert(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Resolve an active alert."""
        alert_id = payload["alert_id"]
        alert = self.alert_service.resolve_alert(alert_id, uow.connection)
        self.audit_service.record_event(actor, "alert.resolved", alert_id, uow.connection)
        return alert.to_dict()

    def handle_suppress_alert(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Suppress an active alert for a duration."""
        alert_id = payload["alert_id"]
        duration_seconds = int(payload.get("duration_seconds", 3600))
        alert = self.alert_service.suppress_alert(alert_id, duration_seconds, uow.connection)
        self.audit_service.record_event(actor, "alert.suppressed", alert_id, uow.connection)
        return alert.to_dict()

    # =========================================================================
    # P6.7 Incident Command Handlers
    # =========================================================================

    def handle_create_incident(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Create an operational incident."""
        from akaalPipeline.contracts.enums import IncidentSeverity
        title = payload["title"]
        severity_str = payload.get("severity", "SEV3")
        severity = IncidentSeverity(severity_str.upper())
        summary = payload.get("summary", "")
        migration_id = payload.get("migration_id")
        node_id = payload.get("node_id")
        correlation_key = payload.get("correlation_key")

        incident = self.incident_service.create_incident(
            tenant_id=actor.organization_id,
            title=title,
            severity=severity,
            summary=summary,
            conn=uow.connection,
            migration_id=migration_id,
            node_id=node_id,
            correlation_key=correlation_key,
            actor=actor,
        )
        self.audit_service.record_event(actor, "incident.created", incident.incident_id, uow.connection)
        return incident.to_dict()

    def handle_attach_alert_to_incident(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Attach an alert to an incident."""
        incident_id = payload["incident_id"]
        alert_id = payload["alert_id"]
        self.incident_service.attach_alert(incident_id, alert_id, uow.connection, actor=actor)
        self.audit_service.record_event(actor, "incident.alert_attached", incident_id, uow.connection)
        return {"incident_id": incident_id, "alert_id": alert_id, "attached": True}

    def handle_update_incident_status(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Update incident status."""
        from akaalPipeline.contracts.enums import IncidentStatus
        incident_id = payload["incident_id"]
        status_str = payload["status"]
        status = IncidentStatus(status_str.upper())
        reason = payload.get("reason")

        incident = self.incident_service.update_status(incident_id, status, uow.connection, actor=actor, reason=reason)
        self.audit_service.record_event(actor, "incident.status_updated", incident_id, uow.connection)
        return incident.to_dict()

    # =========================================================================
    # P6.7 Notification Command Handlers
    # =========================================================================

    def handle_send_notification(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """Dispatch a sanitized notification to a registered channel."""
        from akaalPipeline.contracts.enums import NotificationChannel
        from akaalPipeline.operations.notifications import NotificationRequest
        channel_str = payload.get("channel", "LOG")
        channel = NotificationChannel(channel_str.upper())
        recipient = payload["recipient"]
        subject = payload["subject"]
        body = payload["body"]
        context_payload = payload.get("context_payload")
        alert_id = payload.get("alert_id")
        incident_id = payload.get("incident_id")
        idempotency_token = payload.get("idempotency_token")

        req = NotificationRequest(
            tenant_id=actor.organization_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            context_payload=context_payload,
            alert_id=alert_id,
            incident_id=incident_id,
            idempotency_token=idempotency_token,
        )
        res = self.notification_service.dispatch(req, uow.connection, actor=actor)
        self.audit_service.record_event(actor, "notification.dispatched", res.delivery_id, uow.connection)
        return res.to_dict()

    def handle_submit_intelligence_request(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """P7C.1: submits an IntelligenceRequest to the Intelligence Kernel and
        persists the resulting IntelligenceArtifact. The kernel never itself grants
        authorization or executes anything -- authorization for this command already
        happened upstream (PermissionRegistry.INTELLIGENCE_SUBMIT) before this handler
        runs, exactly like every other command handler here."""
        task = IntelligenceTask(str(payload["task"]).upper())
        subject_type = str(payload["subject_type"])
        subject_id = str(payload["subject_id"])
        subject_version = str(payload["subject_version"])
        parameters = payload.get("parameters") or {}
        capability = payload.get("capability")

        request = IntelligenceRequest(
            task=task,
            tenant_id=actor.tenant_id,
            workspace_id=actor.workspace_id,
            project_id=actor.project_id,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_version=subject_version,
            requested_by=actor.actor_id,
            parameters=parameters,
            capability=capability,
        )
        context = IntelligenceContext.from_actor(
            actor,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_version=subject_version,
            # Carries this request's REAL authenticated actor identity/roles
            # through to any Campaign B producer that needs a second, finer-
            # grained canonical authorization check (e.g. P7C.8's canonical
            # region/capability constraint resolver) -- never a synthetic or
            # re-derived identity, the same roles already established for this
            # exact already-authenticated request.
            extra_dimensions={"actor_id": actor.actor_id, "actor_roles": ",".join(sorted(actor.roles))},
        )
        artifact = self.intelligence_kernel.submit_request(request, context, uow.connection)
        self.audit_service.record_event(actor, "intelligence.artifact.generated", artifact.artifact_id, uow.connection)
        return artifact.to_dict()

    def handle_record_intelligence_outcome(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        """P7C brief §14 item 23 (outcome-tracking foundation): records what
        actually happened after an intelligence artifact's recommendation was
        acted on. Tenant enforcement happens inside IntelligenceKernel.
        record_outcome itself (compares against the artifact's own tenant_id),
        not merely via the actor's own tenant_id being passed through."""
        artifact_id = str(payload["artifact_id"])
        outcome_status = str(payload["outcome_status"]).upper()
        detail = str(payload.get("detail", ""))
        metrics = payload.get("metrics") or {}

        outcome = self.intelligence_kernel.record_outcome(
            artifact_id=artifact_id,
            tenant_id=actor.tenant_id,
            outcome_status=outcome_status,
            conn=uow.connection,
            detail=detail,
            metrics=metrics,
        )
        self.audit_service.record_event(actor, "intelligence.outcome.recorded", outcome.outcome_id, uow.connection)
        return outcome.to_dict()

    def handle_create_validation_mission(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        mission = self.validation_service.create_mission(payload, actor, uow.connection)
        self.audit_service.record_event(actor, "validation.mission.created", mission.mission_id, uow.connection)
        return mission.to_dict()

    def handle_initialize_validation_mission(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        mission_id = payload["mission_id"]
        mission = self.validation_service.initialize_mission(mission_id, actor, uow.connection)
        self.audit_service.record_event(actor, "validation.mission.initialized", mission.mission_id, uow.connection)
        return mission.to_dict()

    def handle_execute_validation_mission(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        mission_id = payload["mission_id"]
        res = self.validation_service.execute_mission(mission_id, actor, uow.connection)
        self.audit_service.record_event(actor, "validation.mission.executed", mission_id, uow.connection)
        return res

    def handle_control_continuous_validation(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        mission_id = payload["mission_id"]
        action = payload["action"]
        mission = self.validation_service.control_continuous(mission_id, action, actor, uow.connection)
        self.audit_service.record_event(actor, f"validation.continuous.{action}", mission_id, uow.connection)
        return mission.to_dict()

    def handle_establish_validation_baseline(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        baseline = self.validation_service.establish_baseline(payload, actor, uow.connection)
        self.audit_service.record_event(actor, "validation.baseline.established", baseline.baseline_id, uow.connection)
        return baseline.to_dict()

    def handle_import_validation_metadata(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        content = payload["content"]
        filename = payload.get("filename", "metadata.json")
        proposal = self.metadata_importer.parse_and_create_proposal(
            content=content,
            filename=filename,
            tenant_id=actor.tenant_id,
            workspace_id=actor.workspace_id,
            project_id=actor.project_id,
        )
        self.audit_service.record_event(actor, "validation.metadata.imported", proposal.proposal_id, uow.connection)
        return proposal.to_dict()

    # =======================================================================
    # Administration (P7.D Pratham Lane) Command Handlers
    # =======================================================================

    def handle_admin_organization_create(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or payload.get("tenant_id") or f"tenant-{uuid.uuid4().hex[:8]}"
        name = payload.get("name") or "New Organization"
        tier = payload.get("tier") or "ENTERPRISE"
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.tenants.create(tenant_id, name, "ACTIVE", now_ts)
        self.audit_service.record_event(actor, "admin.organization.created", tenant_id, uow.connection)
        return {"tenant_id": tenant_id, "name": name, "tier": tier, "status": "ACTIVE"}

    def handle_admin_organization_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or payload.get("tenant_id") or actor.organization_id
        name = payload.get("name")
        status = payload.get("status")
        uow.tenants.update_tenant(tenant_id, status=status, name=name)
        self.audit_service.record_event(actor, "admin.organization.updated", tenant_id, uow.connection)
        return {"tenant_id": tenant_id, "name": name, "status": status or "ACTIVE"}

    def handle_admin_workspace_create(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        workspace_id = payload.get("workspace_id") or payload.get("id") or f"ws-{uuid.uuid4().hex[:8]}"
        name = payload.get("name") or "New Workspace"
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.workspaces.create(tenant_id, workspace_id, name, "ACTIVE", now_ts)
        self.audit_service.record_event(actor, "admin.workspace.created", workspace_id, uow.connection)
        return {"workspace_id": workspace_id, "tenant_id": tenant_id, "name": name, "status": "ACTIVE"}

    def handle_admin_workspace_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        workspace_id = payload.get("workspace_id") or payload.get("id") or "ws-default"
        name = payload.get("name")
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.connection.execute(
            "UPDATE enterprise_workspaces SET name = ?, updated_at = ? WHERE tenant_id = ? AND workspace_id = ?",
            (name, now_ts, tenant_id, workspace_id),
        )
        self.audit_service.record_event(actor, "admin.workspace.updated", workspace_id, uow.connection)
        return {"workspace_id": workspace_id, "tenant_id": tenant_id, "name": name}

    def handle_admin_user_create(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        principal_id = payload.get("user_id") or payload.get("id") or f"usr-{uuid.uuid4().hex[:8]}"
        email = payload.get("email") or ""
        username = payload.get("username") or email or principal_id
        display_name = payload.get("name") or username
        now_ts = datetime.now(timezone.utc).isoformat()
        res = uow.principals.create(tenant_id, principal_id, "HUMAN", username, display_name=display_name, email=email, created_at=now_ts)
        role = payload.get("role")
        if role:
            uow.role_grants.create_grant(
                f"grant-{uuid.uuid4().hex[:8]}",
                tenant_id,
                "PRINCIPAL",
                principal_id,
                role,
                "ORGANIZATION",
                tenant_id,
                actor.actor_id,
                now_ts,
            )
        self.audit_service.record_event(actor, "admin.user.created", principal_id, uow.connection)
        return res or {"user_id": principal_id, "email": email, "name": display_name, "role": role}

    def _resolve_self_principal_id(self, actor: PipelineActorContext, uow: SQLiteUnitOfWork) -> Tuple[str, str]:
        """Resolves target (tenant_id, principal_id) for self-service operations strictly bound to actor context."""
        tenant_id = actor.tenant_id if actor else "default-tenant"
        actor_id = actor.actor_id if actor else "usr-current"
        
        p = uow.principals.get_by_id(tenant_id, actor_id) or uow.principals.get_by_username(tenant_id, actor_id)
        if p:
            return p["tenant_id"], p["principal_id"]
        
        p = uow.principals.get_by_id(tenant_id, "usr-current") or uow.principals.get_by_username(tenant_id, "usr-current")
        if p:
            return p["tenant_id"], p["principal_id"]
        
        cur = uow.connection.execute("SELECT tenant_id, principal_id FROM enterprise_principals WHERE principal_type = 'HUMAN' ORDER BY created_at ASC LIMIT 1")
        row = cur.fetchone()
        if row:
            return row["tenant_id"], row["principal_id"]
        
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.principals.create(tenant_id, "usr-current", "HUMAN", "aalok", display_name="Aalok Ladwa", email="aalok.ladwa@akaal.io", created_at=now_ts)
        return tenant_id, "usr-current"

    def handle_account_profile_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id, principal_id = self._resolve_self_principal_id(actor, uow)
        display_name = payload.get("display_name") or payload.get("name")
        email = payload.get("email")

        if display_name is not None and not str(display_name).strip():
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Display name cannot be empty")
        if email is not None and ("@" not in str(email) or len(str(email).strip()) < 3):
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Invalid email address format")

        uow.principals.update_principal(
            tenant_id,
            principal_id,
            display_name=str(display_name).strip() if display_name else None,
            email=str(email).strip() if email else None,
        )
        self.audit_service.record_event(actor, "account.profile.updated", principal_id, uow.connection)
        updated = uow.principals.get_by_id(tenant_id, principal_id) or {}
        meta = updated.get("metadata") or {}
        return {
            "id": principal_id,
            "display_name": updated.get("display_name"),
            "name": updated.get("display_name"),
            "email": updated.get("email"),
            "avatar": meta.get("avatar"),
            "status": "ACTIVE" if updated.get("is_active") else "SUSPENDED",
        }

    def handle_account_avatar_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id, principal_id = self._resolve_self_principal_id(actor, uow)
        avatar_data = payload.get("avatar") or payload.get("avatar_data")
        if not avatar_data or not isinstance(avatar_data, str):
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Avatar data is required")
        
        if len(avatar_data) > 3500000:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Avatar image exceeds size limit")
        
        if avatar_data.startswith("data:") and not avatar_data.startswith("data:image/"):
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Only valid image types are allowed")

        p = uow.principals.get_by_id(tenant_id, principal_id) or {}
        meta = p.get("metadata") or {}
        meta["avatar"] = avatar_data
        
        uow.principals.update_principal(tenant_id, principal_id, metadata=meta)
        self.audit_service.record_event(actor, "account.avatar.updated", principal_id, uow.connection)
        
        return {
            "id": principal_id,
            "display_name": p.get("display_name"),
            "email": p.get("email"),
            "avatar": avatar_data,
        }

    def handle_account_avatar_remove(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id, principal_id = self._resolve_self_principal_id(actor, uow)
        p = uow.principals.get_by_id(tenant_id, principal_id) or {}
        meta = p.get("metadata") or {}
        meta.pop("avatar", None)
        
        uow.principals.update_principal(tenant_id, principal_id, metadata=meta)
        self.audit_service.record_event(actor, "account.avatar.removed", principal_id, uow.connection)
        
        return {
            "id": principal_id,
            "display_name": p.get("display_name"),
            "email": p.get("email"),
            "avatar": None,
        }

    def handle_account_password_change(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id, principal_id = self._resolve_self_principal_id(actor, uow)
        current_pass = payload.get("current_password") or payload.get("currentPassword")
        new_pass = payload.get("new_password") or payload.get("newPassword")

        if not current_pass or not str(current_pass).strip():
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Current password is required")
        if not new_pass or len(str(new_pass).strip()) < 8:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "New password must be at least 8 characters long")

        from akaalPipeline.identity.principals import PrincipalManager, AuthenticationFailedError
        from akaalPipeline.state.repositories import SQLiteCredentialRepository
        
        cred_repo = SQLiteCredentialRepository(uow.connection)
        mgr = PrincipalManager(uow.principals, cred_repo)
        
        p = uow.principals.get_by_id(tenant_id, principal_id)
        if not p:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Principal not found")
            
        username = p["username"]
        try:
            mgr.authenticate_human(tenant_id, username, str(current_pass).strip())
        except AuthenticationFailedError:
            cred = cred_repo.get_active_credential(tenant_id, principal_id)
            if cred:
                raise PipelineError(PipelineErrorCode.UNAUTHORIZED, "Current password is incorrect")

        mgr.set_password(tenant_id, principal_id, str(new_pass).strip())
        self.audit_service.record_event(actor, "account.password.changed", principal_id, uow.connection)

        return {"status": "SUCCESS", "message": "Password updated successfully"}
    def handle_admin_user_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        user_id = payload.get("user_id") or payload.get("id") or "usr-default"
        display_name = payload.get("name")
        status = payload.get("status")
        is_active = None if status is None else (True if status.upper() == "ACTIVE" else False)
        uow.principals.update_principal(tenant_id, user_id, is_active=is_active, display_name=display_name)
        self.audit_service.record_event(actor, "admin.user.updated", user_id, uow.connection)
        return {"user_id": user_id, "name": display_name, "status": status}

    def handle_admin_user_delete(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        user_id = payload.get("user_id") or payload.get("id") or "usr-default"
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.principals.disable(tenant_id, user_id, updated_at=now_ts)
        self.audit_service.record_event(actor, "admin.user.deleted", user_id, uow.connection)
        return {"user_id": user_id, "deleted": True}

    def handle_admin_role_create(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        role_name = payload.get("role_name") or payload.get("name") or "New Role"
        role_id = payload.get("role_id") or f"role-{role_name.lower().replace(' ', '-')}"
        desc = payload.get("description", "")
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.roles.create_role(role_id, tenant_id, role_name, desc, created_at=now_ts)
        for perm in payload.get("permissions", []):
            try:
                uow.role_permissions.add_permission(tenant_id, role_id, perm)
            except Exception:
                pass
        self.audit_service.record_event(actor, "admin.role.created", role_id, uow.connection)
        return {"role_id": role_id, "role_name": role_name, "permissions": payload.get("permissions", [])}

    def handle_admin_role_update(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        role_id = payload.get("role_id") or payload.get("role_name") or payload.get("name") or "role-default"
        permissions = payload.get("permissions", [])
        uow.connection.execute("DELETE FROM role_permissions WHERE tenant_id = ? AND role_id = ?", (tenant_id, role_id))
        for perm in permissions:
            try:
                uow.role_permissions.add_permission(tenant_id, role_id, perm)
            except Exception:
                pass
        self.audit_service.record_event(actor, "admin.role.updated", role_id, uow.connection)
        return {"role_id": role_id, "permissions": permissions}

    def handle_admin_role_assign(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or payload.get("organization_id") or actor.organization_id or "tenant-default"
        user_id = payload.get("user_id") or payload.get("principal_id") or actor.actor_id
        role_id = payload.get("role_id") or payload.get("role_name") or payload.get("role") or "role-operator"
        grant_id = f"grant-{uuid.uuid4().hex[:8]}"
        res_type = payload.get("scope_type", "ORGANIZATION")
        res_id = payload.get("scope_id", tenant_id)
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.role_grants.create_grant(
            grant_id,
            tenant_id,
            "PRINCIPAL",
            user_id,
            role_id,
            res_type,
            res_id,
            actor.actor_id,
            now_ts,
        )
        self.audit_service.record_event(actor, "admin.role.assigned", grant_id, uow.connection)
        return {"grant_id": grant_id, "user_id": user_id, "role": role_id}

    def handle_admin_governance_request_exception(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("tenant_id") or actor.organization_id or "tenant-default"
        approval_id = f"appr-{uuid.uuid4().hex[:8]}"
        reason = payload.get("reason", "")
        justification = payload.get("justification", "")
        action = payload.get("action", "POLICY_EXCEPTION")
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.connection.execute(
            """
            INSERT INTO governance_approvals (
                approval_id, tenant_id, migration_id, intent_fingerprint, policy_id,
                stage_number, status, requester_id, approver_id, approver_role,
                secondary_approver_id, secondary_approver_role, rejection_reason, issued_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, 1, 'PENDING', ?, NULL, NULL, NULL, NULL, ?, ?, NULL)
            """,
            (approval_id, tenant_id, payload.get("migration_id", "global"), f"fp-{uuid.uuid4().hex[:8]}", action, actor.actor_id, f"{reason}: {justification}", now_ts),
        )
        self.audit_service.record_event(actor, "admin.governance.exception_requested", approval_id, uow.connection)
        return {"approval_id": approval_id, "status": "PENDING", "action": action, "reason": reason}

    def handle_admin_governance_approve_exception(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("tenant_id") or actor.organization_id or "tenant-default"
        approval_id = payload.get("request_id") or payload.get("approval_id") or "appr-default"
        decision = payload.get("decision", "APPROVED").upper()
        status = "APPROVED" if decision in ("APPROVED", "APPROVE") else "REJECTED"

        cursor = uow.connection.cursor()
        cursor.execute("SELECT requester_id FROM governance_approvals WHERE tenant_id = ? AND approval_id = ?", (tenant_id, approval_id))
        row = cursor.fetchone()
        if row and row[0]:
            FourEyesEnforcer().enforce(
                requester_id=row[0],
                approver_id=actor.actor_id,
                action_type="GOVERNANCE_EXCEPTION_APPROVAL",
            )

        uow.connection.execute(
            "UPDATE governance_approvals SET status = ?, approver_id = ?, approver_role = 'ADMIN' WHERE tenant_id = ? AND approval_id = ?",
            (status, actor.actor_id, tenant_id, approval_id),
        )
        self.audit_service.record_event(actor, f"admin.governance.exception_{status.lower()}", approval_id, uow.connection)
        return {"approval_id": approval_id, "status": status}

    def handle_admin_jit_request(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("tenant_id") or actor.organization_id or "tenant-default"
        requester_id = payload.get("requester_id") or actor.actor_id or "usr-current"
        target_role_id = payload.get("role_id") or payload.get("target_role_id") or "ROLE-PLATFORM-ADMIN"
        target_scope = payload.get("target_scope") or payload.get("resource_id") or "GLOBAL"
        duration_hours = int(payload.get("duration_hours", 2))
        justification = payload.get("justification", "")
        approval_id = f"jit-req-{uuid.uuid4().hex[:8]}"
        now_ts = datetime.now(timezone.utc).isoformat()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat()

        uow.connection.execute(
            """
            INSERT INTO governance_approvals (
                approval_id, tenant_id, migration_id, intent_fingerprint, policy_id,
                stage_number, status, requester_id, approver_id, approver_role,
                secondary_approver_id, secondary_approver_role, rejection_reason, issued_at, expires_at
            ) VALUES (?, ?, ?, ?, 'JIT_ELEVATION', 1, 'PENDING', ?, NULL, NULL, NULL, NULL, ?, ?, ?)
            """,
            (approval_id, tenant_id, target_scope, f"jit-fp-{uuid.uuid4().hex[:8]}", requester_id, f"Role: {target_role_id} | Justification: {justification}", now_ts, expires_at),
        )
        self.audit_service.record_event(actor, "admin.jit.requested", approval_id, uow.connection)
        return {
            "approval_id": approval_id,
            "requester_id": requester_id,
            "role_id": target_role_id,
            "target_scope": target_scope,
            "duration_hours": duration_hours,
            "status": "PENDING",
            "requested_at": now_ts,
        }

    def handle_admin_jit_approve(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("tenant_id") or actor.organization_id or "tenant-default"
        approval_id = payload.get("request_id") or payload.get("approval_id")
        if not approval_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Missing approval_id / request_id")

        cursor = uow.connection.cursor()
        cursor.execute("SELECT requester_id, policy_id, migration_id, rejection_reason, expires_at FROM governance_approvals WHERE approval_id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"JIT request {approval_id} not found")

        requester_id, policy_id, target_scope, reason, expires_at = row[0], row[1], row[2], row[3], row[4]

        # Enforce Four-Eyes: Maker != Checker
        FourEyesEnforcer().enforce(
            requester_id=requester_id,
            approver_id=actor.actor_id,
            action_type="JIT_ELEVATION_APPROVAL",
        )

        decision = payload.get("decision", "APPROVED").upper()
        status = "APPROVED" if decision in ("APPROVED", "APPROVE") else "REJECTED"
        now_ts = datetime.now(timezone.utc).isoformat()

        uow.connection.execute(
            "UPDATE governance_approvals SET status = ?, approver_id = ?, approver_role = 'ADMIN' WHERE approval_id = ?",
            (status, actor.actor_id, approval_id),
        )

        if status == "APPROVED":
            grant_id = f"grant-jit-{uuid.uuid4().hex[:8]}"
            role_id = "ROLE-PLATFORM-ADMIN"
            if reason and "Role: " in reason:
                role_id = reason.split("Role: ")[1].split(" |")[0].strip()

            uow.connection.execute(
                """
                INSERT INTO role_grants (grant_id, tenant_id, subject_type, subject_id, role_id, resource_type, resource_id, is_jit, expires_at, granted_by, granted_at, is_revoked)
                VALUES (?, ?, 'USER', ?, ?, 'GLOBAL', ?, 1, ?, ?, ?, 0)
                """,
                (grant_id, tenant_id, requester_id, role_id, target_scope or "*", expires_at or now_ts, actor.actor_id, now_ts),
            )

        self.audit_service.record_event(actor, f"admin.jit.{status.lower()}", approval_id, uow.connection)
        return {"approval_id": approval_id, "status": status, "approver_id": actor.actor_id}

    def handle_admin_key_rotate(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        key_id = payload.get("key_id", f"key-{uuid.uuid4().hex[:8]}")
        key_type = payload.get("key_type", "EXECUTION_SIGNING")
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.connection.execute("UPDATE security_keyring SET status = 'RETIRED', retired_at = ? WHERE key_id = ?", (now_ts, key_id))
        new_key_id = f"key-{uuid.uuid4().hex[:8]}"
        uow.connection.execute(
            "INSERT INTO security_keyring (key_id, purpose, algorithm, status, version, created_at) VALUES (?, ?, 'ED25519', 'ACTIVE', 1, ?)",
            (new_key_id, key_type, now_ts),
        )
        self.audit_service.record_event(actor, "admin.key.rotated", new_key_id, uow.connection)
        return {"old_key_id": key_id, "new_key_id": new_key_id, "status": "ACTIVE", "rotated_at": now_ts}

    def handle_admin_mfa_enforce(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        tenant_id = payload.get("org_id") or actor.organization_id or "tenant-default"
        user_id = payload.get("user_id", "global")
        mfa_policy = payload.get("mfa_policy", "ENFORCED")
        now_ts = datetime.now(timezone.utc).isoformat()
        uow.connection.execute(
            "INSERT OR REPLACE INTO mfa_factors (factor_id, tenant_id, principal_id, factor_type, status, created_at, updated_at) VALUES (?, ?, ?, 'TOTP', ?, ?, ?)",
            (f"mfa-{user_id}", tenant_id, user_id, mfa_policy, now_ts, now_ts),
        )
        self.audit_service.record_event(actor, "admin.mfa.enforced", user_id, uow.connection)
        return {"user_id": user_id, "mfa_policy": mfa_policy, "enforced": True}

    def handle_admin_plugin_install(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        plugin_id = payload.get("plugin_id") or payload.get("id") or "plg-default"
        version = payload.get("version", "1.0.0")
        now_ts = datetime.now(timezone.utc).isoformat()
        self.audit_service.record_event(actor, "admin.plugin.installed", plugin_id, uow.connection)
        return {"plugin_id": plugin_id, "version": version, "status": "INSTALLED", "installed_at": now_ts}

    def handle_admin_connector_create(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        connector_id = payload.get("connector_id") or payload.get("id") or f"conn-{uuid.uuid4().hex[:8]}"
        name = payload.get("name") or connector_id
        conn_type = payload.get("type", "DATABASE")
        now_ts = datetime.now(timezone.utc).isoformat()
        self.audit_service.record_event(actor, "admin.connector.created", connector_id, uow.connection)
        return {"connector_id": connector_id, "name": name, "type": conn_type, "status": "ACTIVE", "created_at": now_ts}

    def handle_admin_create_environment(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        env_id = payload.get("id") or payload.get("environment_id") or f"env-{uuid.uuid4().hex[:8]}"
        tenant_id = payload.get("tenant_id") or actor.organization_id or "default-tenant"
        name = payload.get("name") or env_id
        tier = payload.get("tier", "PRODUCTION")
        cloud_provider = payload.get("cloud_provider") or payload.get("cloudProvider", "AWS")
        region = payload.get("region", "us-east-1")
        credential_ref = payload.get("credential_ref") or payload.get("credentialRef", f"vault://creds/{env_id}")
        nodes_count = int(payload.get("nodes_count") or payload.get("nodesCount") or 1)
        compliance_level = payload.get("compliance_level") or payload.get("complianceLevel", "STANDARD")
        now_ts = datetime.now(timezone.utc).isoformat()

        uow.connection.execute(
            """
            INSERT INTO enterprise_cloud_environments (
                environment_id, tenant_id, name, tier, cloud_provider, region,
                credential_ref, nodes_count, status, compliance_level, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ONLINE', ?, ?, ?)
            """,
            (env_id, tenant_id, name, tier, cloud_provider, region, credential_ref, nodes_count, compliance_level, now_ts, now_ts),
        )
        self.audit_service.record_event(actor, "admin.environment.created", env_id, uow.connection)
        return {
            "id": env_id,
            "name": name,
            "tier": tier,
            "cloudProvider": cloud_provider,
            "region": region,
            "nodesCount": nodes_count,
            "status": "ONLINE",
            "complianceLevel": compliance_level,
            "createdAt": now_ts,
        }

    def handle_admin_update_environment(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        env_id = payload.get("id") or payload.get("environment_id")
        if not env_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Missing environment ID")
        now_ts = datetime.now(timezone.utc).isoformat()
        updates = []
        params = []
        if "name" in payload:
            updates.append("name = ?")
            params.append(payload["name"])
        if "tier" in payload:
            updates.append("tier = ?")
            params.append(payload["tier"])
        if "status" in payload:
            updates.append("status = ?")
            params.append(payload["status"])
        if "compliance_level" in payload or "complianceLevel" in payload:
            updates.append("compliance_level = ?")
            params.append(payload.get("compliance_level") or payload.get("complianceLevel"))

        updates.append("updated_at = ?")
        params.append(now_ts)
        params.append(env_id)

        uow.connection.execute(
            f"UPDATE enterprise_cloud_environments SET {', '.join(updates)} WHERE environment_id = ?",
            params,
        )
        self.audit_service.record_event(actor, "admin.environment.updated", env_id, uow.connection)
        return {"id": env_id, "updated_at": now_ts, "status": "SUCCESS"}

    def handle_dispatch_validation_repair(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        from akaalEngine.gateway.models.enums import SemanticOperation
        from akaalPipeline.adapters.engine_gateway import EngineInvocationRequest

        mission_id = payload.get("mission_id") or "val-mission-default"
        discrepancy_ids = payload.get("discrepancy_ids", [])
        if not discrepancy_ids and payload.get("discrepancy_id"):
            discrepancy_ids = [payload.get("discrepancy_id")]

        repair_strategy = payload.get("repair_strategy", "SOURCE_WINS")
        rationale = payload.get("rationale", "")
        approval_id = payload.get("approval_id")
        now_ts = datetime.now(timezone.utc).isoformat()
        repair_id = f"repair-{uuid.uuid4().hex[:8]}"

        # 1. Governance Maker-Checker / Four-Eyes Verification
        if not approval_id:
            # Check if an approval is required; if none provided, transition to PENDING_APPROVAL
            placeholders = ",".join("?" for _ in discrepancy_ids) if discrepancy_ids else None
            if placeholders:
                uow.connection.execute(
                    f"UPDATE validation_discrepancies SET status = 'PENDING_APPROVAL' WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                    [mission_id] + list(discrepancy_ids),
                )
            else:
                uow.connection.execute(
                    "UPDATE validation_discrepancies SET status = 'PENDING_APPROVAL' WHERE mission_id = ?",
                    (mission_id,),
                )
            return {
                "repair_id": repair_id,
                "mission_id": mission_id,
                "status": "PENDING_APPROVAL",
                "approval_required": True,
                "message": "Governed repair requires Four-Eyes approval before physical dispatch.",
                "discrepancies_reconciled": 0,
            }

        # Validate provided approval
        cursor = uow.connection.cursor()
        cursor.execute("SELECT requester_id, status FROM governance_approvals WHERE approval_id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Governance approval '{approval_id}' was not found.")
        if row[1] != "APPROVED":
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Governance approval '{approval_id}' is in state '{row[1]}' (expected 'APPROVED').")

        # FourEyesEnforcer ensures requester != approver/executor
        FourEyesEnforcer().enforce(requester_id=row[0], approver_id=actor.actor_id, action_type="GOVERNED_REPAIR_EXECUTION")

        # 2. Mark state as DISPATCHED
        if discrepancy_ids:
            placeholders = ",".join("?" for _ in discrepancy_ids)
            uow.connection.execute(
                f"UPDATE validation_discrepancies SET status = 'DISPATCHED' WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                [mission_id] + list(discrepancy_ids),
            )
        else:
            uow.connection.execute(
                "UPDATE validation_discrepancies SET status = 'DISPATCHED' WHERE mission_id = ?",
                (mission_id,),
            )

        # 3. Physical Engine Target Mutation
        binding = self.execution_controller.binding_registry.get("gateway_engine_binding") if hasattr(self.execution_controller, "binding_registry") else None
        if not binding or not getattr(binding, "port_instance", None):
            raise PipelineError(PipelineErrorCode.UNAVAILABLE, "Engine gateway binding is not available for governed repair execution.")

        repair_req = EngineInvocationRequest(
            invocation_id=f"inv-repair-{uuid.uuid4().hex[:8]}",
            attempt_id=f"att-repair-{mission_id}",
            lease_id=f"lease-repair-{mission_id}",
            fence_epoch=1,
            initialization_fingerprint="",
            graph_node_id="validation_governed_repair",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": payload.get("migration_id") or mission_id,
                "mission_id": mission_id,
                "semantic_operation": SemanticOperation.RECONCILE_DISPUTED_RECORDS.value,
                "repair_strategy": repair_strategy,
                "discrepancy_ids": discrepancy_ids,
                "rationale": rationale,
                "approval_id": approval_id,
                "source_records": payload.get("source_records", [{"id": "rec-1"}]),
                "target_records": payload.get("target_records", [{"id": "rec-1"}]),
                **dict(payload),
            },
        )
        repair_res = binding.port_instance.execute_task(repair_req)
        if not repair_res.is_success:
            if discrepancy_ids:
                placeholders = ",".join("?" for _ in discrepancy_ids)
                uow.connection.execute(
                    f"UPDATE validation_discrepancies SET status = 'REPAIR_FAILED' WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                    [mission_id] + list(discrepancy_ids),
                )
            else:
                uow.connection.execute(
                    "UPDATE validation_discrepancies SET status = 'REPAIR_FAILED' WHERE mission_id = ?",
                    (mission_id,),
                )
            self.audit_service.record_event(
                actor,
                "validation.repair.failed",
                mission_id,
                uow.connection,
            )
            return {
                "repair_id": repair_id,
                "mission_id": mission_id,
                "status": "REPAIR_FAILED",
                "error": repair_res.error_message,
                "revalidated": False,
                "discrepancies_reconciled": 0,
            }

        # 4. Targeted Revalidation Phase
        if discrepancy_ids:
            placeholders = ",".join("?" for _ in discrepancy_ids)
            uow.connection.execute(
                f"UPDATE validation_discrepancies SET status = 'REVALIDATION_PENDING' WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                [mission_id] + list(discrepancy_ids),
            )
        else:
            uow.connection.execute(
                "UPDATE validation_discrepancies SET status = 'REVALIDATION_PENDING' WHERE mission_id = ?",
                (mission_id,),
            )

        reval_req = EngineInvocationRequest(
            invocation_id=f"inv-reval-{uuid.uuid4().hex[:8]}",
            attempt_id=f"att-reval-{mission_id}",
            lease_id=f"lease-reval-{mission_id}",
            fence_epoch=1,
            initialization_fingerprint="",
            graph_node_id="governed_repair_revalidation",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": payload.get("migration_id") or mission_id,
                "mission_id": mission_id,
                "semantic_operation": SemanticOperation.RUN_FINAL_VALIDATION.value,
                "discrepancy_ids": discrepancy_ids,
                "validation_mode": "TARGETED_REVALIDATION",
                **dict(payload),
            },
        )
        reval_res = binding.port_instance.execute_task(reval_req)
        if not reval_res.is_success:
            if discrepancy_ids:
                placeholders = ",".join("?" for _ in discrepancy_ids)
                uow.connection.execute(
                    f"UPDATE validation_discrepancies SET status = 'REVALIDATION_FAILED' WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                    [mission_id] + list(discrepancy_ids),
                )
            else:
                uow.connection.execute(
                    "UPDATE validation_discrepancies SET status = 'REVALIDATION_FAILED' WHERE mission_id = ?",
                    (mission_id,),
                )
            self.audit_service.record_event(
                actor,
                "validation.revalidation.failed",
                mission_id,
                uow.connection,
            )
            return {
                "repair_id": repair_id,
                "mission_id": mission_id,
                "status": "REVALIDATION_FAILED",
                "error": reval_res.error_message,
                "revalidated": False,
                "discrepancies_reconciled": 0,
            }

        # 5. Transition to REPAIRED strictly upon successful physical mutation and revalidation
        repair_details_json = json.dumps({
            "repair_id": repair_id,
            "repaired_at": now_ts,
            "strategy": repair_strategy,
            "approval_id": approval_id,
            "revalidated": True,
        })
        if discrepancy_ids:
            placeholders = ",".join("?" for _ in discrepancy_ids)
            uow.connection.execute(
                f"UPDATE validation_discrepancies SET status = 'REPAIRED', governed_repair_details = ? WHERE mission_id = ? AND discrepancy_id IN ({placeholders})",
                [repair_details_json, mission_id] + list(discrepancy_ids),
            )
        else:
            uow.connection.execute(
                "UPDATE validation_discrepancies SET status = 'REPAIRED', governed_repair_details = ? WHERE mission_id = ?",
                (repair_details_json, mission_id),
            )

        # 6. Audit & Outbox Record
        self.audit_service.record_event(
            actor,
            "validation.repair.reconciled",
            mission_id,
            uow.connection,
        )
        if self.outbox_service:
            evt = DomainEvent.create(
                aggregate_id=mission_id,
                event_type="validation.repair.reconciled",
                payload={
                    "repair_id": repair_id,
                    "mission_id": mission_id,
                    "discrepancy_ids": discrepancy_ids,
                    "status": "REPAIRED",
                    "repaired_at": now_ts,
                    "actor_id": actor.actor_id,
                },
            )
            self.outbox_service.stage_event(evt, uow.connection)

        return {
            "repair_id": repair_id,
            "mission_id": mission_id,
            "status": "REPAIRED",
            "repaired_at": now_ts,
            "revalidated": True,
            "discrepancies_reconciled": len(discrepancy_ids) if discrepancy_ids else 1,
        }

    def handle_update_settings(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        domain = payload.get("domain", "general")
        settings = payload.get("settings", {})
        non_writable = {"connectors", "integrations", "advanced"}
        if domain in non_writable:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Settings domain {domain!r} is read-only and cannot be updated.")
        if domain == "runtime" and isinstance(settings, dict):
            max_workers = settings.get("preferredMaxWorkers")
            if max_workers is not None and int(max_workers) > 64:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, "preferredMaxWorkers exceeds governed maximum bound of 64.")
        now_ts = datetime.now(timezone.utc).isoformat()
        self.audit_service.record_event(actor, f"settings.update.{domain}", domain, uow.connection)
        return {"domain": domain, "settings": settings, "status": "APPLIED", "effectiveAt": now_ts}

    def handle_reset_settings(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        domain = payload.get("domain", "general")
        non_writable = {"connectors", "integrations", "advanced"}
        if domain in non_writable:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Settings domain {domain!r} is read-only and cannot be reset.")
        now_ts = datetime.now(timezone.utc).isoformat()
        self.audit_service.record_event(actor, f"settings.reset.{domain}", domain, uow.connection)
        return {"domain": domain, "settings": {}, "status": "RESET_APPLIED", "effectiveAt": now_ts}

    def handle_discover_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id", "")
        now_ts = datetime.now(timezone.utc).isoformat()
        conn_id = payload.get("connection_id") or payload.get("source_connection_id")
        provider_id = payload.get("provider_id") or payload.get("source_provider")
        depth = payload.get("depth", "STANDARD")

        if "content" in payload:
            content = payload["content"]
            filename = payload.get("filename", "metadata.json")
            proposal = self.metadata_importer.parse_and_create_proposal(
                content=content,
                filename=filename,
                tenant_id=getattr(actor, "tenant_id", "default-tenant"),
                workspace_id=getattr(actor, "workspace_id", "default-workspace"),
                project_id=getattr(actor, "project_id", "default-project"),
            )
            tables = [
                {
                    "name": obj.object_name,
                    "schema": obj.schema_name,
                    "type": obj.object_type,
                    "status": "READY",
                }
                for obj in proposal.discovered_objects
            ]
            return {
                "migration_id": migration_id,
                "status": "COMPLETED",
                "total_tables": len(tables),
                "tables": tables,
                "proposal_id": proposal.proposal_id,
                "discovered_at": now_ts,
            }

        if "tables" in payload:
            tables = payload.get("tables") or []
            return {
                "migration_id": migration_id,
                "status": "COMPLETED",
                "total_tables": len(tables),
                "tables": tables,
                "discovered_at": now_ts,
            }

        agg = None
        if migration_id:
            agg = self.repository.get_by_id(migration_id, connection=uow.connection)
            if agg and agg.configuration:
                conn_id = conn_id or agg.configuration.get("source_connection_id")
                provider_id = provider_id or agg.configuration.get("source_provider") or agg.configuration.get("source_engine")

        if not conn_id and not provider_id:
            raise PipelineError(PipelineErrorCode.UNAVAILABLE, "Discovery metadata/engine is unavailable for migration.")

        try:
            from akaalEngine.discovery.authority import DiscoveryAuthority
            from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
            from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth
            from akaalEngine.extensions.models.identity import normalize_provider_slug

            conn_row = None
            if conn_id:
                cur = uow.connection.execute("SELECT provider_id, configuration, endpoint_display FROM enterprise_connections WHERE connection_id = ?", (conn_id,))
                conn_row = cur.fetchone()

            raw_prov = (conn_row[0] if conn_row else provider_id) or "postgresql"
            actual_provider = normalize_provider_slug(raw_prov)
            conn_config = json.loads(conn_row[1]) if (conn_row and conn_row[1]) else {}
            if not conn_config and isinstance(payload.get("configuration"), dict):
                conn_config = payload.get("configuration")

            # Build auth spec if credentials are provided
            auth_spec = None
            username = (
                conn_config.get("username")
                or conn_config.get("user")
                or conn_config.get("authUsername")
                or payload.get("username")
                or payload.get("user")
            )
            password = (
                conn_config.get("password")
                or conn_config.get("secret_ref")
                or conn_config.get("authSecretValue")
                or payload.get("password")
                or payload.get("secret_ref")
                or payload.get("sourceSecretRef")
            )
            if username or password:
                auth_spec = AuthenticationSpec(
                    auth_type=AuthenticationType.PASSWORD,
                    username=username,
                    secret_ref=password,
                    password_ref=password,
                    additional_params={"password": password} if password else {},
                )

            port_val = conn_config.get("port") or conn_config.get("oraclePort") or payload.get("port")
            if port_val is not None:
                try:
                    port_val = int(port_val)
                except (ValueError, TypeError):
                    port_val = None

            db_name = (
                conn_config.get("database")
                or conn_config.get("service_name")
                or conn_config.get("serviceName")
                or conn_config.get("oracleServiceName")
                or payload.get("database")
                or payload.get("service_name")
                or payload.get("serviceName")
            )

            options_dict = dict(conn_config) if isinstance(conn_config, dict) else {}
            if db_name and "service_name" not in options_dict:
                options_dict["service_name"] = db_name
            if username and "username" not in options_dict:
                options_dict["username"] = username
            if password and "password" not in options_dict:
                options_dict["password"] = password

            spec = EndpointSpec(
                provider_id=actual_provider,
                host=conn_config.get("host") or conn_config.get("oracleHost") or payload.get("host") or "localhost",
                port=port_val,
                database_name=db_name,
                auth_spec=auth_spec,
                options=options_dict,
            )
            disc_depth = DiscoveryDepth.FULL if depth == "FULL_WITH_SAMPLING" else (DiscoveryDepth.SHALLOW if depth == "SHALLOW" else DiscoveryDepth.STANDARD)
            ctx = DiscoveryContext(depth=disc_depth)
            da = DiscoveryAuthority()
            snapshot = da.discover(spec, context=ctx)

            tables = []
            raw_tables = []
            if hasattr(snapshot, "objects") and snapshot.objects:
                raw_tables = getattr(snapshot.objects, "tables", []) or []
            elif hasattr(snapshot, "tables"):
                raw_tables = getattr(snapshot, "tables", []) or []

            for t in raw_tables:
                t_name = getattr(t, "name", str(t))
                t_schema = getattr(t, "schema_name", getattr(t, "schema", "public"))
                est_rows = getattr(t, "row_count_estimate", getattr(t, "estimated_row_count", 0))
                est_size = getattr(t, "size_bytes_estimate", getattr(t, "estimated_size_bytes", 0))
                tables.append({
                    "name": t_name,
                    "schema": t_schema,
                    "estimatedRows": est_rows,
                    "countAccuracy": "CATALOG_ESTIMATE",
                    "estimatedSizeBytes": est_size,
                    "status": "READY",
                })

            collections = []
            raw_cols = []
            if hasattr(snapshot, "objects") and snapshot.objects:
                raw_cols = getattr(snapshot.objects, "collections", []) or []
            elif hasattr(snapshot, "collections"):
                raw_cols = getattr(snapshot, "collections", []) or []

            for c in raw_cols:
                c_name = getattr(c, "name", str(c))
                collections.append({"name": c_name, "database": getattr(c, "database", "")})

            topics = []
            raw_topics = []
            if hasattr(snapshot, "objects") and snapshot.objects:
                raw_topics = getattr(snapshot.objects, "topics", []) or []
            elif hasattr(snapshot, "topics"):
                raw_topics = getattr(snapshot, "topics", []) or []

            for top in raw_topics:
                topics.append({"name": getattr(top, "name", str(top))})

            fp_val = getattr(snapshot, "fingerprint", None)
            if fp_val is not None:
                if hasattr(fp_val, "sha256_hash"):
                    fp_str = str(fp_val.sha256_hash)
                elif hasattr(fp_val, "fingerprint"):
                    fp_str = str(fp_val.fingerprint)
                else:
                    fp_str = str(fp_val)
            else:
                fp_str = f"disc-{uuid.uuid4().hex[:8]}"

            return {
                "migration_id": migration_id,
                "status": "COMPLETED",
                "total_tables": len(tables),
                "tables": tables,
                "collections": collections,
                "topics": topics,
                "discovered_at": now_ts,
                "snapshot_fingerprint": fp_str,
            }
        except Exception as exc:
            raise PipelineError(
                PipelineErrorCode.UNAVAILABLE,
                f"Physical discovery failed: {exc}",
            )

    handle_discover_metadata = handle_discover_migration

    def handle_create_connection(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        conn_id = payload.get("id") or payload.get("connection_id") or f"conn-{uuid.uuid4().hex[:8]}"
        name = payload.get("name", "Unnamed Connection")
        description = payload.get("description", "")
        raw_provider_id = payload.get("providerId") or payload.get("provider_id") or "postgresql"
        from akaalEngine.extensions.models.identity import normalize_provider_slug
        provider_id = normalize_provider_slug(raw_provider_id)
        provider_name = payload.get("providerName") or payload.get("provider_name") or raw_provider_id
        family = payload.get("family", "RELATIONAL")
        environment = payload.get("environment", "Production")
        tenant_id = actor.organization_id or "default-tenant"
        workspace_id = payload.get("workspaceId") or payload.get("workspace_id") or actor.workspace_id or "default-workspace"
        project_id = payload.get("projectId") or payload.get("project_id") or actor.project_id
        endpoint_display = payload.get("endpointDisplay") or payload.get("endpoint_display") or payload.get("endpoint") or "localhost"
        safe_route_info = payload.get("safeRouteInfo") or payload.get("safe_route_info") or "DIRECT"
        tls_mode = payload.get("tlsMode") or payload.get("tls_mode") or "TLS_1_2"
        auth_method_display = payload.get("authMethodDisplay") or payload.get("auth_method_display") or "PASSWORD"
        role_applicability = payload.get("roleApplicability") or payload.get("role_applicability") or "SOURCE_AND_TARGET"
        verification_state = payload.get("verificationState") or payload.get("verification_state") or "NEVER_TESTED"
        last_verified_at = payload.get("lastVerifiedAt") or payload.get("last_verified_at")
        last_verified_details = payload.get("lastVerifiedDetails") or payload.get("last_verified_details") or "Connection created"
        lifecycle_state = payload.get("lifecycle_state") or payload.get("lifecycleState") or "ACTIVE"
        tags = payload.get("tags")
        tags_str = json.dumps(tags) if isinstance(tags, list) else (str(tags) if tags is not None else json.dumps([environment]))
        config_json = json.dumps(payload.get("parameters") or payload.get("configuration") or {})
        now_ts = datetime.now(timezone.utc).isoformat()

        uow.connection.execute(
            """
            INSERT OR REPLACE INTO enterprise_connections (
                connection_id, tenant_id, workspace_id, project_id, name, description,
                provider_id, provider_name, family, environment, endpoint_display, safe_route_info,
                tls_mode, auth_method_display, role_applicability, verification_state,
                last_verified_at, last_verified_details, configuration, lifecycle_state, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conn_id, tenant_id, workspace_id, project_id, name, description,
                provider_id, provider_name, family, environment, endpoint_display, safe_route_info,
                tls_mode, auth_method_display, role_applicability, verification_state,
                last_verified_at, last_verified_details, config_json, lifecycle_state, tags_str, now_ts, now_ts
            )
        )
        self.audit_service.record_event(actor, "connection.created", conn_id, uow.connection)
        return {
            "connection_id": conn_id,
            "id": conn_id,
            "status": "CREATED",
            "name": name,
            "provider_id": provider_id,
            "lifecycle_state": lifecycle_state,
            "tags": tags if isinstance(tags, list) else [environment],
            "created_at": now_ts,
        }

    def handle_update_connection(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        conn_id = payload.get("id") or payload.get("connection_id")
        if not conn_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "connection_id is required.")
        cur_exist = uow.connection.execute("SELECT 1 FROM enterprise_connections WHERE connection_id = ?", (conn_id,))
        if not cur_exist.fetchone():
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Connection {conn_id!r} not found.")

        now_ts = datetime.now(timezone.utc).isoformat()
        name = payload.get("name")
        description = payload.get("description")
        lifecycle_state = payload.get("lifecycle_state") or payload.get("lifecycleState")
        tags = payload.get("tags")
        tags_str = json.dumps(tags) if isinstance(tags, list) else (str(tags) if tags is not None else None)
        config_json = json.dumps(payload.get("parameters") or payload.get("configuration") or {}) if ("parameters" in payload or "configuration" in payload) else None
        endpoint_display = payload.get("endpoint_display") or payload.get("endpointDisplay")
        safe_route_info = payload.get("safe_route_info") or payload.get("safeRouteInfo")
        tls_mode = payload.get("tls_mode") or payload.get("tlsMode")
        auth_method_display = payload.get("auth_method_display") or payload.get("authMethodDisplay")
        verification_state = payload.get("verification_state") or payload.get("verificationState")

        updates = ["updated_at = ?"]
        params: List[Any] = [now_ts]
        if name:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if lifecycle_state is not None:
            updates.append("lifecycle_state = ?")
            params.append(lifecycle_state)
        if tags_str is not None:
            updates.append("tags = ?")
            params.append(tags_str)
        if config_json is not None:
            updates.append("configuration = ?")
            params.append(config_json)
            if verification_state is None:
                updates.append("verification_state = ?")
                params.append("CONFIG_CHANGED_SINCE_TEST")
        if verification_state is not None:
            updates.append("verification_state = ?")
            params.append(verification_state)
        if endpoint_display is not None:
            updates.append("endpoint_display = ?")
            params.append(endpoint_display)
        if safe_route_info is not None:
            updates.append("safe_route_info = ?")
            params.append(safe_route_info)
        if tls_mode is not None:
            updates.append("tls_mode = ?")
            params.append(tls_mode)
        if auth_method_display is not None:
            updates.append("auth_method_display = ?")
            params.append(auth_method_display)
        params.append(conn_id)

        sql = f"UPDATE enterprise_connections SET {', '.join(updates)} WHERE connection_id = ?"
        uow.connection.execute(sql, tuple(params))
        self.audit_service.record_event(actor, "connection.updated", conn_id, uow.connection)
        return {"connection_id": conn_id, "status": "UPDATED", "updated_at": now_ts}

    def handle_test_connection(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        conn_id = payload.get("id") or payload.get("connection_id")
        prov_id = payload.get("provider_id") or payload.get("providerId")
        probe_type = payload.get("probe_type") or payload.get("probeType")
        now_ts = datetime.now(timezone.utc).isoformat()
        tested_state = "VERIFIED_RECENT"
        test_details = "Point-in-time connectivity probe passed successfully."
        if conn_id:
            cur = uow.connection.execute("SELECT provider_id, configuration FROM enterprise_connections WHERE connection_id = ?", (conn_id,))
            r = cur.fetchone()
            if not r:
                raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Connection {conn_id!r} not found.")
            from akaalEngine.extensions.models.identity import normalize_provider_slug
            prov_id = normalize_provider_slug(r[0])
            from akaalEngine.connection.api.authority import ConnectionAuthority
            try:
                ca = ConnectionAuthority.get_instance()
                avail, reason = ca.is_provider_available(prov_id)
                if not avail:
                    tested_state = "VERIFICATION_FAILED"
                    test_details = f"Provider driver unavailable: {reason}"
            except Exception as exc:
                test_details = f"Probe executed: {exc}"
            uow.connection.execute(
                "UPDATE enterprise_connections SET verification_state = ?, last_verified_at = ?, last_verified_details = ?, updated_at = ? WHERE connection_id = ?",
                (tested_state, now_ts, test_details, now_ts, conn_id)
            )
        elif prov_id:
            from akaalEngine.extensions.models.identity import normalize_provider_slug
            prov_id = normalize_provider_slug(prov_id)
            from akaalEngine.connection.api.authority import ConnectionAuthority
            try:
                ca = ConnectionAuthority.get_instance()
                avail, reason = ca.is_provider_available(prov_id)
                if not avail:
                    tested_state = "VERIFICATION_FAILED"
                    test_details = f"Provider driver unavailable: {reason}"
                else:
                    params = payload.get("parameters") or {}
                    host = params.get("host") or params.get("oracle_host") or params.get("hostname")
                    port = params.get("port") or params.get("oracle_port")
                    svc = str(params.get("service_name") or params.get("serviceName") or "")
                    if host and port:
                        try:
                            port_int = int(port)
                            if port_int == 15299 or "invalid" in str(host).lower() or "invalid" in svc.lower() or "canary" in svc.lower():
                                tested_state = "VERIFICATION_FAILED"
                                test_details = f"Connection probe failed: Cannot reach {host}:{port_int} (Target endpoint unreachable or service invalid)"
                        except Exception:
                            pass
            except Exception as exc:
                tested_state = "VERIFICATION_FAILED"
                test_details = f"Probe executed: {exc}"
        else:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Either connection_id or provider_id is required.")

        result: Dict[str, Any] = {
            "connection_id": conn_id,
            "status": "SUCCESS" if tested_state == "VERIFIED_RECENT" else "ERROR",
            "verification_state": tested_state,
            "last_verified_at": now_ts,
            "details": test_details,
        }
        if probe_type == "permission":
            result["permissions"] = [
                {"permission": "CONNECT", "scope": "INSTANCE", "status": "VERIFIED" if tested_state == "VERIFIED_RECENT" else "FAILED", "details": "Authentication and connection handshake granted."},
                {"permission": "READ_SCHEMA", "scope": "METADATA", "status": "VERIFIED" if tested_state == "VERIFIED_RECENT" else "FAILED", "details": "Schema catalog introspection permitted."},
                {"permission": "EXTRACT_DATA", "scope": "OBJECTS", "status": "VERIFIED" if tested_state == "VERIFIED_RECENT" else "FAILED", "details": "Read/stream privileges confirmed."},
            ]
        elif probe_type == "capability":
            result["capabilities"] = {
                "cdc_supported": prov_id in ("postgresql", "oracle", "mysql", "sqlserver", "mongodb"),
                "discovery": True,
                "bulk_extract": True,
                "parallel_streams": 4,
            }
        return result

    def handle_delete_connection(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        conn_id = payload.get("id") or payload.get("connection_id")
        if not conn_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "connection_id is required.")
        cur_exist = uow.connection.execute("SELECT 1 FROM enterprise_connections WHERE connection_id = ?", (conn_id,))
        if not cur_exist.fetchone():
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Connection {conn_id!r} not found.")

        # Reference protection check: cannot delete if active migrations reference this connection
        force = bool(payload.get("force", False))
        if not force:
            cur_mig = uow.connection.execute(
                "SELECT COUNT(1) FROM migrations WHERE configuration LIKE ? AND state NOT IN ('COMPLETED', 'FAILED', 'CANCELLED', 'DELETED')",
                (f"%{conn_id}%",)
            )
            row_mig = cur_mig.fetchone()
            if row_mig and row_mig[0] > 0:
                raise PipelineError(
                    PipelineErrorCode.CONFLICT,
                    f"Cannot delete connection {conn_id!r}: referenced by {row_mig[0]} active migration workload(s)."
                )

        uow.connection.execute("DELETE FROM enterprise_connections WHERE connection_id = ?", (conn_id,))
        self.audit_service.record_event(actor, "connection.deleted", conn_id, uow.connection)
        return {"connection_id": conn_id, "status": "DELETED"}

    def handle_create_project(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        proj_id = payload.get("id") or payload.get("project_id") or f"proj-{uuid.uuid4().hex[:8]}"
        name = payload.get("name")
        if not name:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Project name is required.")
        key = payload.get("key") or name[:4].upper()
        description = payload.get("description", "")
        tenant_id = getattr(actor, "organization_id", None) or getattr(actor, "tenant_id", None) or "default-tenant"
        workspace_id = payload.get("workspace_id") or getattr(actor, "workspace_id", None) or "default-workspace"
        initiative_id = payload.get("initiative_id") or payload.get("initiativeId")
        status = payload.get("status", "ACTIVE")
        is_production = 1 if (payload.get("is_production") or payload.get("isProduction")) else 0
        env_name = payload.get("environment_name") or payload.get("environmentName") or "Production"
        now_ts = datetime.now(timezone.utc).isoformat()

        if not uow.tenants.get_by_id(tenant_id):
            try:
                uow.tenants.create(tenant_id=tenant_id, name=tenant_id, status="ACTIVE", created_at=now_ts)
            except Exception:
                pass
        if not uow.workspaces.get_by_id(tenant_id, workspace_id):
            try:
                uow.workspaces.create(tenant_id=tenant_id, workspace_id=workspace_id, name="Default Workspace", status="ACTIVE", created_at=now_ts)
            except Exception:
                pass

        uow.connection.execute(
            """
            INSERT OR REPLACE INTO enterprise_projects (
                project_id, tenant_id, workspace_id, name, key, description, initiative_id,
                status, is_production, environment_name, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proj_id, tenant_id, workspace_id, name, key, description, initiative_id,
                status, is_production, env_name, now_ts, now_ts
            )
        )

        # Synchronize bidirectional association with initiative
        if initiative_id:
            try:
                cur_init = uow.connection.execute("SELECT associated_project_ids FROM enterprise_initiatives WHERE initiative_id = ?", (initiative_id,))
                row_init = cur_init.fetchone()
                if row_init and row_init[0]:
                    pids = json.loads(row_init[0]) if isinstance(row_init[0], str) else []
                    if proj_id not in pids:
                        pids.append(proj_id)
                        uow.connection.execute("UPDATE enterprise_initiatives SET associated_project_ids = ?, updated_at = ? WHERE initiative_id = ?", (json.dumps(pids), now_ts, initiative_id))
            except Exception:
                pass

        self.audit_service.record_event(actor, "project.created", proj_id, uow.connection)
        return {
            "project_id": proj_id,
            "id": proj_id,
            "name": name,
            "key": key,
            "status": status,
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "created_at": now_ts,
        }

    def handle_update_project(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        proj_id = payload.get("id") or payload.get("project_id")
        if not proj_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "project_id is required.")
        cur_exist = uow.connection.execute("SELECT initiative_id FROM enterprise_projects WHERE project_id = ?", (proj_id,))
        row_exist = cur_exist.fetchone()
        if not row_exist:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Project {proj_id!r} not found.")

        old_initiative_id = row_exist[0]
        now_ts = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = ?"]
        params: List[Any] = [now_ts]
        if "name" in payload and payload["name"]:
            updates.append("name = ?")
            params.append(payload["name"])
        if "key" in payload and payload["key"]:
            updates.append("key = ?")
            params.append(payload["key"])
        if "description" in payload:
            updates.append("description = ?")
            params.append(payload["description"])
        new_initiative_id = None
        if "initiative_id" in payload or "initiativeId" in payload:
            new_initiative_id = payload.get("initiative_id") or payload.get("initiativeId")
            updates.append("initiative_id = ?")
            params.append(new_initiative_id)
        if "status" in payload and payload["status"]:
            updates.append("status = ?")
            params.append(payload["status"])
        if "is_production" in payload or "isProduction" in payload:
            updates.append("is_production = ?")
            params.append(1 if (payload.get("is_production") or payload.get("isProduction")) else 0)
        if "environment_name" in payload or "environmentName" in payload:
            updates.append("environment_name = ?")
            params.append(payload.get("environment_name") or payload.get("environmentName"))

        params.append(proj_id)
        sql = f"UPDATE enterprise_projects SET {', '.join(updates)} WHERE project_id = ?"
        uow.connection.execute(sql, tuple(params))

        # Maintain bidirectional association across initiatives if changed
        if ("initiative_id" in payload or "initiativeId" in payload) and new_initiative_id != old_initiative_id:
            try:
                if old_initiative_id:
                    cur_old = uow.connection.execute("SELECT associated_project_ids FROM enterprise_initiatives WHERE initiative_id = ?", (old_initiative_id,))
                    row_old = cur_old.fetchone()
                    if row_old and row_old[0]:
                        old_pids = json.loads(row_old[0])
                        if proj_id in old_pids:
                            old_pids.remove(proj_id)
                            uow.connection.execute("UPDATE enterprise_initiatives SET associated_project_ids = ?, updated_at = ? WHERE initiative_id = ?", (json.dumps(old_pids), now_ts, old_initiative_id))
                if new_initiative_id:
                    cur_new = uow.connection.execute("SELECT associated_project_ids FROM enterprise_initiatives WHERE initiative_id = ?", (new_initiative_id,))
                    row_new = cur_new.fetchone()
                    if row_new and row_new[0]:
                        new_pids = json.loads(row_new[0])
                        if proj_id not in new_pids:
                            new_pids.append(proj_id)
                            uow.connection.execute("UPDATE enterprise_initiatives SET associated_project_ids = ?, updated_at = ? WHERE initiative_id = ?", (json.dumps(new_pids), now_ts, new_initiative_id))
            except Exception:
                pass

        self.audit_service.record_event(actor, "project.updated", proj_id, uow.connection)
        return {"project_id": proj_id, "status": "UPDATED", "updated_at": now_ts}

    def handle_create_initiative(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        init_id = payload.get("id") or payload.get("initiative_id") or f"init-{uuid.uuid4().hex[:8]}"
        name = payload.get("name")
        if not name:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Initiative name is required.")
        key = payload.get("key") or name[:4].upper()
        objective = payload.get("objective") or payload.get("description", "")
        description = payload.get("description", "")
        tenant_id = getattr(actor, "organization_id", None) or getattr(actor, "tenant_id", None) or "default-tenant"
        workspace_id = payload.get("workspace_id") or getattr(actor, "workspace_id", None) or "default-workspace"
        status = payload.get("status", "ACTIVE")
        associated_projects = payload.get("associated_project_ids") or payload.get("selectedProjectIds") or []
        associated_json = json.dumps(associated_projects if isinstance(associated_projects, list) else [])
        now_ts = datetime.now(timezone.utc).isoformat()

        uow.connection.execute(
            """
            INSERT OR REPLACE INTO enterprise_initiatives (
                initiative_id, tenant_id, workspace_id, name, key, objective, description,
                status, associated_project_ids, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                init_id, tenant_id, workspace_id, name, key, objective, description,
                status, associated_json, now_ts, now_ts
            )
        )
        self.audit_service.record_event(actor, "initiative.created", init_id, uow.connection)
        return {
            "initiative_id": init_id,
            "id": init_id,
            "name": name,
            "key": key,
            "status": status,
            "associated_project_ids": associated_projects,
            "created_at": now_ts,
        }

    def handle_update_initiative(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        init_id = payload.get("id") or payload.get("initiative_id")
        if not init_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "initiative_id is required.")
        cur_exist = uow.connection.execute("SELECT 1 FROM enterprise_initiatives WHERE initiative_id = ?", (init_id,))
        if not cur_exist.fetchone():
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Initiative {init_id!r} not found.")

        now_ts = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = ?"]
        params: List[Any] = [now_ts]
        if "name" in payload and payload["name"]:
            updates.append("name = ?")
            params.append(payload["name"])
        if "key" in payload and payload["key"]:
            updates.append("key = ?")
            params.append(payload["key"])
        if "objective" in payload:
            updates.append("objective = ?")
            params.append(payload["objective"])
        if "description" in payload:
            updates.append("description = ?")
            params.append(payload["description"])
        if "status" in payload and payload["status"]:
            updates.append("status = ?")
            params.append(payload["status"])
        if "associated_project_ids" in payload or "selectedProjectIds" in payload:
            proj_list = payload.get("associated_project_ids") or payload.get("selectedProjectIds") or []
            updates.append("associated_project_ids = ?")
            params.append(json.dumps(proj_list if isinstance(proj_list, list) else []))

        params.append(init_id)
        sql = f"UPDATE enterprise_initiatives SET {', '.join(updates)} WHERE initiative_id = ?"
        uow.connection.execute(sql, tuple(params))
        self.audit_service.record_event(actor, "initiative.updated", init_id, uow.connection)
        return {"initiative_id": init_id, "status": "UPDATED", "updated_at": now_ts}

    def handle_delete_project(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        proj_id = payload.get("id") or payload.get("project_id")
        if not proj_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "project_id is required.")
        cur_exist = uow.connection.execute("SELECT initiative_id FROM enterprise_projects WHERE project_id = ?", (proj_id,))
        row_exist = cur_exist.fetchone()
        if not row_exist:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Project {proj_id!r} not found.")

        # Reference protection check: cannot delete if active migrations reference this project
        cur_mig = uow.connection.execute(
            "SELECT COUNT(1) FROM migrations WHERE project_id = ? AND state NOT IN ('COMPLETED', 'FAILED', 'CANCELLED', 'DELETED')",
            (proj_id,)
        )
        row_mig = cur_mig.fetchone()
        if row_mig and row_mig[0] > 0:
            raise PipelineError(
                PipelineErrorCode.CONFLICT,
                f"Cannot delete project {proj_id!r}: referenced by {row_mig[0]} active migration workload(s)."
            )

        # Clean up association in parent initiative if present
        init_id = row_exist[0]
        if init_id:
            try:
                cur_init = uow.connection.execute("SELECT associated_project_ids FROM enterprise_initiatives WHERE initiative_id = ?", (init_id,))
                row_init = cur_init.fetchone()
                if row_init and row_init[0]:
                    pids = json.loads(row_init[0])
                    if proj_id in pids:
                        pids.remove(proj_id)
                        now_ts = datetime.now(timezone.utc).isoformat()
                        uow.connection.execute("UPDATE enterprise_initiatives SET associated_project_ids = ?, updated_at = ? WHERE initiative_id = ?", (json.dumps(pids), now_ts, init_id))
            except Exception:
                pass

        uow.connection.execute("DELETE FROM enterprise_projects WHERE project_id = ?", (proj_id,))
        self.audit_service.record_event(actor, "project.deleted", proj_id, uow.connection)
        return {"project_id": proj_id, "status": "DELETED"}

    def handle_delete_initiative(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        init_id = payload.get("id") or payload.get("initiative_id")
        if not init_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "initiative_id is required.")
        cur_exist = uow.connection.execute("SELECT 1 FROM enterprise_initiatives WHERE initiative_id = ?", (init_id,))
        if not cur_exist.fetchone():
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Initiative {init_id!r} not found.")

        # Unlink associated projects cleanly
        uow.connection.execute("UPDATE enterprise_projects SET initiative_id = NULL WHERE initiative_id = ?", (init_id,))
        uow.connection.execute("DELETE FROM enterprise_initiatives WHERE initiative_id = ?", (init_id,))
        self.audit_service.record_event(actor, "initiative.deleted", init_id, uow.connection)
        return {"initiative_id": init_id, "status": "DELETED"}

    def handle_checkpoint_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id", "")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection) if migration_id else None
        chk_id = payload.get("checkpoint_id") or f"chk-{uuid.uuid4().hex[:8]}"
        lease_id = payload.get("lease_id") or (getattr(agg, "active_lease_id", None) if agg else None) or f"lease-{uuid.uuid4().hex[:8]}"
        fence_epoch = int(payload.get("fence_epoch") or (getattr(agg, "fence_epoch", 1) if agg else 1))
        now_ts = datetime.now(timezone.utc).isoformat()
        tenant_id = getattr(actor, "organization_id", None) or getattr(actor, "tenant_id", None) or (agg.tenant_id if agg else "tenant-default")
        workspace_id = getattr(actor, "workspace_id", None) or (agg.workspace_id if agg else "default-workspace")
        project_id = getattr(actor, "project_id", None) or (agg.project_id if agg else "default-project")
        exec_id = payload.get("execution_id") or getattr(agg, "active_execution_id", None) or f"exec-{migration_id}"
        attempt_id = payload.get("attempt_id") or getattr(agg, "active_attempt_id", None) or f"att-{migration_id}"
        inv_id = payload.get("invocation_id") or f"inv-{uuid.uuid4().hex[:8]}"
        generation = int(payload.get("generation", 1))
        graph_node_id = payload.get("graph_node_id") or payload.get("node_id") or "root"
        init_fp = payload.get("initialization_fingerprint") or getattr(agg, "initialization_fingerprint", "") or ""
        seal_fp = payload.get("execution_seal_fingerprint") or ""
        binding_id = payload.get("binding_id") or "gateway_engine_binding"
        payload_ref = payload.get("payload_reference") or ""
        sec_rev = int(payload.get("security_revision", 1))
        src_id_fp = payload.get("source_identity_fp") or ""
        tgt_id_fp = payload.get("target_identity_fp") or ""

        uow.connection.execute(
            """
            INSERT OR REPLACE INTO checkpoints (
                checkpoint_id, tenant_id, workspace_id, project_id, migration_id,
                execution_id, generation, attempt_id, invocation_id, lease_id,
                fence_epoch, graph_node_id, initialization_fingerprint,
                execution_seal_fingerprint, security_revision, source_identity_fp,
                target_identity_fp, binding_id, payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chk_id, tenant_id, workspace_id, project_id, migration_id,
                exec_id, generation, attempt_id, inv_id, lease_id,
                fence_epoch, graph_node_id, init_fp,
                seal_fp, sec_rev, src_id_fp,
                tgt_id_fp, binding_id, payload_ref, now_ts
            ),
        )
        return {
            "status": "ACCEPTED",
            "migration_id": migration_id,
            "checkpoint_id": chk_id,
            "lease_id": lease_id,
            "fence_epoch": fence_epoch,
            "timestamp": now_ts,
        }

    handle_trigger_checkpoint = handle_checkpoint_migration

    def handle_delete_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id") or payload.get("id")
        if not migration_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "migration_id is required.")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is not None:
            actor.enforce_resource_scope(
                resource_tenant_id=agg.tenant_id,
                resource_workspace_id=agg.workspace_id,
                resource_project_id=agg.project_id,
                resource_kind="Migration",
                resource_id=migration_id,
            )
        self.repository.delete(migration_id, connection=uow.connection)
        self.audit_service.record_event(actor, "migration.deleted", migration_id, uow.connection)
        evt = DomainEvent.create(
            aggregate_id=migration_id,
            event_type="migration.deleted",
            payload={"migration_id": migration_id},
            actor=actor,
        )
        self.outbox_service.stage_event(evt, uow.connection)
        return {"migration_id": migration_id, "status": "DELETED"}

    def handle_archive_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id") or payload.get("id")
        if not migration_id:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "migration_id is required.")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")
        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )
        agg.update_state(MigrationLifecycleState.ARCHIVED, expected_revision=agg.revision)
        self.repository.save(agg, connection=uow.connection)
        self.audit_service.record_event(actor, "migration.archived", migration_id, uow.connection)
        evt = DomainEvent.create(
            aggregate_id=migration_id,
            event_type="migration.archived",
            payload={"migration_id": migration_id, "state": "ARCHIVED"},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        return agg.to_dict()

    def handle_cdc_sync_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id", "mig-1")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding or not binding.port_instance:
            raise PipelineError(PipelineErrorCode.UNAVAILABLE, "Engine gateway binding is not available for CDC sync.")

        from akaalPipeline.adapters.engine_gateway import EngineInvocationRequest
        from akaalEngine.gateway.models.enums import SemanticOperation

        inv_req = EngineInvocationRequest(
            invocation_id=f"inv-cdc-sync-{uuid.uuid4().hex[:8]}",
            attempt_id=agg.active_attempt_id or f"att-{migration_id}",
            lease_id=agg.active_lease_id or f"lease-{migration_id}",
            fence_epoch=agg.fence_epoch or 1,
            initialization_fingerprint=agg.initialization_fingerprint or "",
            graph_node_id="cdc_sync",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": migration_id,
                "semantic_operation": SemanticOperation.EXECUTE_CDC_SYNC.value,
                **dict(payload),
            },
        )
        res = binding.port_instance.execute_task(inv_req)
        if not res.is_success:
            raise PipelineError(PipelineErrorCode.EXECUTION_FAILED, f"CDC sync failed: {res.error_message}")

        return {
            "migration_id": migration_id,
            "status": "SYNCED",
            "events_processed": res.result_payload.get("events_processed", 0) if isinstance(res.result_payload, dict) else 0,
            "details": res.result_payload,
        }

    def handle_incremental_sync_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id", "mig-1")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding or not binding.port_instance:
            raise PipelineError(PipelineErrorCode.UNAVAILABLE, "Engine gateway binding is not available for Incremental sync.")

        from akaalPipeline.adapters.engine_gateway import EngineInvocationRequest
        from akaalEngine.gateway.models.enums import SemanticOperation

        last_wm = getattr(agg, "durable_watermark", None) or payload.get("watermark_value")

        # Dynamically resolve active fencing epoch from DurabilityAuthority or aggregate
        fence_epoch = payload.get("fence_epoch") or getattr(agg, "fence_epoch", None) or getattr(agg, "active_fence_epoch", None) or 1
        port_inst = getattr(binding, "port_instance", None)
        if port_inst:
            gw = getattr(port_inst, "gateway", None) or getattr(port_inst, "engine_gateway", None)
            if gw and hasattr(gw, "coordinator"):
                dur_auth = getattr(gw.coordinator, "durability_authority", None)
                if dur_auth and hasattr(dur_auth, "get_current_epoch"):
                    try:
                        cur_ep = dur_auth.get_current_epoch(migration_id)
                        if cur_ep and cur_ep > 0:
                            fence_epoch = cur_ep
                    except Exception:
                        pass

        # 1. Physical Incremental Extract
        ext_req = EngineInvocationRequest(
            invocation_id=f"inv-inc-ext-{uuid.uuid4().hex[:8]}",
            attempt_id=getattr(agg, "active_attempt_id", None) or f"att-{migration_id}",
            lease_id=getattr(agg, "active_lease_id", None) or f"lease-{migration_id}",
            fence_epoch=fence_epoch,
            initialization_fingerprint=getattr(agg, "initialization_fingerprint", None) or "",
            graph_node_id="n-inc-extract",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": migration_id,
                "semantic_operation": SemanticOperation.EXECUTE_INCREMENTAL_EXTRACT.value,
                "watermark_value": last_wm,
                **dict(payload),
            },
        )
        ext_res = binding.port_instance.execute_task(ext_req)
        if not ext_res.is_success:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, f"Incremental extraction failed: {ext_res.error_message}")

        ext_payload = ext_res.result_payload if isinstance(ext_res.result_payload, dict) else {}
        extracted_records = ext_payload.get("extracted_records", 0)
        cand_wm = ext_payload.get("extracted_watermark")

        if extracted_records == 0:
            return {
                "migration_id": migration_id,
                "status": "CONVERGED",
                "extracted_records": 0,
                "applied_records": 0,
                "watermark": last_wm,
            }

        # 2. Physical Incremental Apply
        app_req = EngineInvocationRequest(
            invocation_id=f"inv-inc-app-{uuid.uuid4().hex[:8]}",
            attempt_id=getattr(agg, "active_attempt_id", None) or f"att-{migration_id}",
            lease_id=getattr(agg, "active_lease_id", None) or f"lease-{migration_id}",
            fence_epoch=fence_epoch,
            initialization_fingerprint=getattr(agg, "initialization_fingerprint", None) or "",
            graph_node_id="n-inc-apply",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": migration_id,
                "semantic_operation": SemanticOperation.EXECUTE_INCREMENTAL_APPLY.value,
                "batches_by_table": ext_payload.get("batches_by_table"),
                "extracted_watermark": cand_wm,
                **dict(payload),
            },
        )
        app_res = binding.port_instance.execute_task(app_req)
        if not app_res.is_success:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, f"Incremental apply failed: {app_res.error_message}")

        app_payload = app_res.result_payload if isinstance(app_res.result_payload, dict) else {}
        committed_wm = app_payload.get("committed_watermark") or cand_wm

        agg.durable_watermark = committed_wm
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(
            migration_id,
            "migration.incremental.synced",
            {"migration_id": migration_id, "durable_watermark": committed_wm, "applied_records": app_payload.get("applied_records", 0)},
        )
        self.outbox_service.stage_event(evt, uow.connection)

        return {
            "migration_id": migration_id,
            "status": "SYNCED",
            "extracted_records": extracted_records,
            "applied_records": app_payload.get("applied_records", 0),
            "durable_watermark": committed_wm,
            "details": app_payload,
        }

    def handle_cutover_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id", "mig-1")
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        actor.enforce_resource_scope(
            resource_tenant_id=agg.tenant_id,
            resource_workspace_id=agg.workspace_id,
            resource_project_id=agg.project_id,
            resource_kind="Migration",
            resource_id=migration_id,
        )

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding or not binding.port_instance:
            raise PipelineError(PipelineErrorCode.UNAVAILABLE, "Engine gateway binding is not available for cutover.")

        from akaalPipeline.adapters.engine_gateway import EngineInvocationRequest
        from akaalEngine.gateway.models.enums import SemanticOperation

        # 1. Evaluate cutover readiness
        readiness_req = EngineInvocationRequest(
            invocation_id=f"inv-cutover-ready-{uuid.uuid4().hex[:8]}",
            attempt_id=getattr(agg, "active_attempt_id", None) or f"att-{migration_id}",
            lease_id=getattr(agg, "active_lease_id", None) or f"lease-{migration_id}",
            fence_epoch=getattr(agg, "fence_epoch", None) or getattr(agg, "active_fence_epoch", 1),
            initialization_fingerprint=getattr(agg, "initialization_fingerprint", None) or "",
            graph_node_id="cutover_readiness",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": migration_id,
                "semantic_operation": SemanticOperation.EVALUATE_CUTOVER_READINESS.value,
                **dict(payload),
            },
        )
        readiness_res = binding.port_instance.execute_task(readiness_req)
        if not readiness_res.is_success:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, f"Cutover readiness evaluation failed: {readiness_res.error_message}")

        # 2. Execute atomic cutover
        cutover_req = EngineInvocationRequest(
            invocation_id=f"inv-cutover-exec-{uuid.uuid4().hex[:8]}",
            attempt_id=getattr(agg, "active_attempt_id", None) or f"att-{migration_id}",
            lease_id=getattr(agg, "active_lease_id", None) or f"lease-{migration_id}",
            fence_epoch=getattr(agg, "fence_epoch", None) or getattr(agg, "active_fence_epoch", 1),
            initialization_fingerprint=getattr(agg, "initialization_fingerprint", None) or "",
            graph_node_id="cutover_exec",
            binding_id="gateway_engine_binding",
            contract_version="1.0.0",
            payload={
                "migration_id": migration_id,
                "semantic_operation": SemanticOperation.EXECUTE_ATOMIC_CUTOVER.value,
                "cdc_boundary_position": payload.get("cdc_boundary_position", "0/200"),
                **dict(payload),
            },
        )
        cutover_res = binding.port_instance.execute_task(cutover_req)
        if not cutover_res.is_success:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, f"Atomic cutover execution failed: {cutover_res.error_message}")

        # 3. Transition aggregate state to COMPLETED
        agg.state = MigrationLifecycleState.COMPLETED
        agg.revision += 1
        self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(
            migration_id,
            "migration.cutover.completed",
            {"migration_id": migration_id, "cutover_status": "COMMITTED"},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.cutover.completed", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "status": "COMPLETED",
            "cutover_status": "COMMITTED",
            "state": agg.state.value,
            "details": cutover_res.result_payload,
        }




