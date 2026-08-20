"""akaalPipeline.application.command_handlers
===========================================
CommandHandlerRegistry mapping command request types to transaction handlers.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Mapping
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.execution.controller import PipelineExecutionController
from akaalPipeline.identity.lineage import LineageTracker
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.history import LifecycleHistoryRecord
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


class CommandHandlerRegistry:
    def __init__(
        self,
        repository: SQLiteMigrationRepository,
        operation_service: OperationService,
        idempotency_service: IdempotencyService,
        execution_controller: PipelineExecutionController,
    ) -> None:
        self.repository = repository
        self.operation_service = operation_service
        self.idempotency_service = idempotency_service
        self.execution_controller = execution_controller

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
            tenant_id=actor.organization_id,
            workspace_id=actor.workspace_id,
            project_id=actor.project_id,
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

        return agg.to_dict()
