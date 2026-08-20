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


class PipelineQueryService:
    def __init__(
        self,
        repository: MigrationRepositoryPort,
        operation_service: OperationService,
    ) -> None:
        self.repository = repository
        self.operation_service = operation_service

    def get_migration(self, migration_id: str, conn: Optional[sqlite3.Connection] = None) -> MigrationAggregate:
        agg = self.repository.get_by_id(migration_id, connection=conn)
        if agg is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Migration {migration_id!r} not found.")
        return agg

    def list_migrations(self, tenant_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[MigrationAggregate]:
        return self.repository.list_all(tenant_id=tenant_id, connection=conn)

    def get_operation(self, operation_id: str, conn: sqlite3.Connection) -> OperationRecord:
        op = self.operation_service.get_by_id(operation_id, conn)
        if op is None:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Operation {operation_id!r} not found.")
        return op
