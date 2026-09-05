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

logger = logging.getLogger(__name__)

from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact
from akaal.governance.foureyes.validator import FourEyesValidator


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

        from akaalPipeline.operations.schedules import ScheduleService
        from akaalPipeline.operations.retention import OperationalRetentionService
        from akaalPipeline.operations.capacity import CapacityIntelligenceService
        from akaalPipeline.operations.alerts import AlertService
        from akaalPipeline.operations.incidents import IncidentService
        from akaalPipeline.operations.notifications import NotificationService

        self.schedule_service = ScheduleService(self.execution_controller.lease_manager)
        self.retention_service = OperationalRetentionService()
        self.capacity_service = CapacityIntelligenceService()
        self.alert_service = AlertService()
        self.incident_service = IncidentService()
        self.notification_service = NotificationService()




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
        decision = PolicyDecision(
            decision_id=decision_id,
            policy_version=payload.get("policy_version", "1.0.0"),
            subject=PolicySubject(actor_id=subject_actor_id, actor_type=payload.get("subject_actor_type", "user"), roles=subject_roles),
            action=PolicyAction(name=payload.get("action", "migration.start")),
            resource=PolicyResource(resource_id=migration_id, resource_type="migration", artifact_fingerprint=target_fp),
            result=PolicyResult.ALLOW,
            reason=payload.get("reason", "Approved by authorized governance actor"),
            issuer_id=actor.actor_id,
            issuer_roles=list(actor.roles),
            effective_at=payload.get("effective_at", datetime.now(timezone.utc).isoformat()),
            expires_at=payload.get("expires_at"),
        )

        approval_art = ImmutableArtifact.create(approval_id, "policy_decision", decision.to_dict())
        self.artifact_registry.register(approval_art, conn=uow.connection)

        # Update aggregate state to AUTHORIZED if it was GOVERNANCE_PENDING
        if agg.state == MigrationLifecycleState.GOVERNANCE_PENDING:
            old_state = agg.state.value
            agg.state = MigrationLifecycleState.AUTHORIZED
            agg.revision += 1
            self.repository.save(agg, connection=uow.connection)

        evt = DomainEvent.create(
            migration_id,
            "migration.approved",
            {"decision_id": decision_id, "approval_id": approval_id, "issuer_id": actor.actor_id},
        )
        self.outbox_service.stage_event(evt, uow.connection)
        self.audit_service.record_event(actor, "migration.approved", migration_id, uow.connection)

        return {
            "migration_id": migration_id,
            "decision_id": decision_id,
            "approval_id": approval_id,
            "result": "ALLOW",
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

        # Idempotent return if already active
        if agg.state == MigrationLifecycleState.ACTIVE:
            return {
                "migration_id": migration_id,
                "status": "APPLIED",
                "state": agg.state.value,
                "message": "Migration is already active.",
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

        # Step 2: Physical task resume in Engine
        cur_running = uow.connection.execute(
            "SELECT current_engine_task_id FROM node_executions WHERE migration_id = ? AND state IN ('PAUSED', 'RUNNING', 'DISPATCHED')",
            (migration_id,),
        )
        paused_tasks = [r["current_engine_task_id"] for r in cur_running.fetchall() if r and r["current_engine_task_id"]]

        binding = self.execution_controller.binding_registry.get("gateway_engine_binding")
        if not binding:
            for b in self.execution_controller.binding_registry.list_all():
                if isinstance(getattr(b, "port_instance", None), ExecutionPort):
                    binding = b
                    break

        if paused_tasks and binding and isinstance(binding.port_instance, ExecutionPort):
            for t_id in paused_tasks:
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



