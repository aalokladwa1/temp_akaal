"""akaalPipeline.application.command_handlers
===========================================
CommandHandlerRegistry mapping command request types to transaction handlers.
"""

from __future__ import annotations

import json
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


from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact


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




    def handle_create_migration(
        self,
        payload: Mapping[str, Any],
        actor: PipelineActorContext,
        uow: SQLiteUnitOfWork,
    ) -> Mapping[str, Any]:
        migration_id = payload.get("migration_id") or f"mig-{uuid.uuid4().hex}"
        name = payload.get("name") or f"Migration {migration_id}"
        mode_str = payload.get("mode") or "M1"

        try:
            mode = MigrationMode(mode_str)
        except ValueError:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unknown migration mode {mode_str!r}")

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

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

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
    ) -> Mapping[str, Any]:
        migration_id = payload["migration_id"]
        agg = self.repository.get_by_id(migration_id, connection=uow.connection)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

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
                    correlation_id=f"cancel-fence-{migration_id}",
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
                        correlation_id=f"cancel-{migration_id}",
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

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

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

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

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

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

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

        if agg.tenant_id != actor.organization_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
        if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
        if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
            raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

        # Require admin or governor role to issue approval
        if not any(r in ("admin", "governor", "security_officer", "compliance") for r in actor.roles):
            raise PipelineError(
                PipelineErrorCode.POLICY_DENIED,
                f"Actor {actor.actor_id!r} lacks governance authorization to approve migration.",
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
