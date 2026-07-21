"""
AKAAL Platform 5 — EvolutionExecutor

Executes forward schema change statements against database context.
"""

from typing import Any, List
from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.domain.errors import ExecutionError


class EvolutionExecutor:
    """Executes ordered schema changes against target database context."""

    def execute_changes(self, changes: List[BaseSchemaChange], db_context: Any = None) -> bool:
        for change in changes:
            if not change.execute(db_context):
                raise ExecutionError(
                    message=f"Failed forward DDL execution for change '{change.change_id}'.",
                    recovery_recommendation="Rollback transaction and restore schema snapshot."
                )
        return True
