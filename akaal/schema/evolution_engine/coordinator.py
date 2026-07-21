"""
AKAAL Platform 5 — EvolutionExecutor & EvolutionCoordinator

Executes transactional live schema evolution steps with partial failure recovery and verification hooks.
"""

from typing import Any, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.domain.enums import EvolutionState, TransactionState
from akaal.schema.domain.errors import ExecutionError
from akaal.schema.evolution_engine.executor import EvolutionExecutor
from akaal.schema.evolution_engine.state_machine import EvolutionStateMachine
from akaal.schema.graph.dependency_graph import ConstraintDependencyGraph
from akaal.schema.observability.logger import StructuredAuditLogger
from akaal.schema.transactions.manager import TransactionManager
from akaal.schema.transactions.model import SchemaTransaction
from akaal.schema.validation.pipeline import ValidationPipeline


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


class EvolutionCoordinator:
    """Coordinates validation, transaction setup, execution ordering, and rollback."""

    def __init__(self, tx_manager: Optional[TransactionManager] = None) -> None:
        self.tx_manager = tx_manager or TransactionManager()
        self.validation_pipeline = ValidationPipeline()
        self.executor = EvolutionExecutor()
        self.audit_logger = StructuredAuditLogger("akaal.schema.evolution")

    def coordinate_evolution(self, changes: List[BaseSchemaChange], db_context: Any = None) -> SchemaTransaction:
        dep_graph = ConstraintDependencyGraph()
        for ch in changes:
            dep_graph.add_change(ch)
        ordered_changes = dep_graph.compute_execution_order()

        tx = self.tx_manager.begin_transaction(changes=ordered_changes)

        try:
            self.tx_manager.transition_state(tx, TransactionState.VALIDATING)
            self.validation_pipeline.validate(ordered_changes, db_context)

            self.tx_manager.transition_state(tx, TransactionState.EXECUTING)
            self.executor.execute_changes(ordered_changes, db_context)

            self.tx_manager.commit(tx)
            self.audit_logger.log_event("EVOLUTION_SUCCESSFUL", details={"tx_id": str(tx.tx_id)})
            return tx
        except Exception as e:
            self.audit_logger.log_event("EVOLUTION_FAILED", level="ERROR", details={"tx_id": str(tx.tx_id), "error": str(e)})
            self.tx_manager.rollback(tx, executor_ctx=db_context)
            raise
