"""akaalPipeline.application.query_service
========================================
Pipeline side-effect-free query service.
"""

from __future__ import annotations

import sqlite3
from typing import Any, List, Mapping, Optional
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.service import OperationService
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import MigrationRepositoryPort


from akaalPipeline.security.context import PipelineActorContext


class PipelineQueryService:
    def __init__(
        self,
        repository: MigrationRepositoryPort,
        operation_service: OperationService,
    ) -> None:
        self.repository = repository
        self.operation_service = operation_service

    def get_migration(
        self,
        migration_id: str,
        actor: Optional[PipelineActorContext] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> MigrationAggregate:
        agg = self.repository.get_by_id(migration_id, connection=conn)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")

        if actor is not None:
            if agg.tenant_id and agg.tenant_id != actor.organization_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} not found or unauthorized for tenant.")
            if actor.workspace_id and agg.workspace_id and agg.workspace_id != actor.workspace_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different workspace.")
            if actor.project_id and agg.project_id and agg.project_id != actor.project_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Migration {migration_id!r} belongs to a different project.")

        return agg

    def list_migrations(
        self,
        actor: Optional[PipelineActorContext] = None,
        tenant_id: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[MigrationAggregate]:
        effective_tenant = actor.organization_id if actor else tenant_id
        migrations = self.repository.list_all(tenant_id=effective_tenant, connection=conn)
        if actor and actor.workspace_id:
            migrations = [m for m in migrations if not m.workspace_id or m.workspace_id == actor.workspace_id]
        if actor and actor.project_id:
            migrations = [m for m in migrations if not m.project_id or m.project_id == actor.project_id]
        return migrations


    def get_operation(
        self,
        operation_id: str,
        actor: Optional[PipelineActorContext] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> OperationRecord:
        if conn is None:
            raise PipelineError(PipelineErrorCode.INTERNAL_ERROR, "Database connection required for get_operation.")
        op = self.operation_service.get_by_id(operation_id, conn)
        if op is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Operation {operation_id!r} not found.")

        if actor is not None:
            op_org = getattr(op.actor, "organization_id", None)
            if op_org and op_org != actor.organization_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} not found or unauthorized for tenant.")
            op_ws = getattr(op.actor, "workspace_id", None)
            if actor.workspace_id and op_ws and op_ws != actor.workspace_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} belongs to a different workspace.")
            op_proj = getattr(op.actor, "project_id", None)
            if actor.project_id and op_proj and op_proj != actor.project_id:
                raise PipelineError(PipelineErrorCode.POLICY_DENIED, f"Operation {operation_id!r} belongs to a different project.")
        return op
