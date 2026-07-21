"""
AKAAL Platform 5 — TransactionManager

Coordinates transaction creation, nested child transactions, validation transitions, commit, and rollback.
"""

import time
from typing import Any, List, Optional

from akaal.schema.domain.changes import BaseSchemaChange
from akaal.schema.domain.enums import TransactionState
from akaal.schema.domain.errors import TransactionError
from akaal.schema.domain.identifiers import TransactionID
from akaal.schema.observability.logger import StructuredAuditLogger
from akaal.schema.transactions.model import RollbackPlan, SchemaTransaction
from akaal.schema.transactions.persistence import TransactionStore


class TransactionManager:
    """Manager managing the lifecycle of SchemaTransactions."""

    def __init__(self, store: Optional[TransactionStore] = None) -> None:
        self.store = store or TransactionStore()
        self.audit_logger = StructuredAuditLogger("akaal.schema.transactions")

    def begin_transaction(self, changes: Optional[List[BaseSchemaChange]] = None, parent_tx_id: Optional[TransactionID] = None) -> SchemaTransaction:
        tx_id = TransactionID.generate()
        tx = SchemaTransaction(
            tx_id=tx_id,
            parent_tx_id=parent_tx_id,
            changes=changes or [],
        )

        # Generate default rollback plan from changes in reverse
        rb_stmts = []
        if changes:
            for ch in reversed(changes):
                rb_stmts.extend(ch.generate_rollback_ddl())
        tx.rollback_plan = RollbackPlan(rollback_statements=rb_stmts)

        tx.add_audit_entry("BEGIN_TRANSACTION", {"parent_tx_id": str(parent_tx_id) if parent_tx_id else None})
        self.store.save_transaction(tx)
        self.audit_logger.log_event("TRANSACTION_BEGUN", details={"tx_id": str(tx_id)})
        return tx

    def transition_state(self, tx: SchemaTransaction, target_state: TransactionState) -> None:
        tx.state_machine.transition_to(target_state)
        tx.add_audit_entry("STATE_TRANSITION", {"target_state": target_state.value})
        if target_state in (TransactionState.COMMITTED, TransactionState.ROLLED_BACK, TransactionState.FAILED):
            tx.completed_at = time.time()
        self.store.save_transaction(tx)
        self.audit_logger.log_event("TRANSACTION_STATE_CHANGED", details={"tx_id": str(tx.tx_id), "new_state": target_state.value})

    def commit(self, tx: SchemaTransaction) -> None:
        if tx.state != TransactionState.EXECUTING:
            raise TransactionError(
                message=f"Cannot commit transaction '{tx.tx_id}' from state '{tx.state.value}'. Expected EXECUTING.",
                recovery_recommendation="Verify execution phase completed cleanly before commit."
            )
        self.transition_state(tx, TransactionState.COMMITTED)

    def rollback(self, tx: SchemaTransaction, executor_ctx: Optional[Any] = None) -> None:
        self.transition_state(tx, TransactionState.ROLLING_BACK)
        try:
            if executor_ctx and hasattr(executor_ctx, "execute_statement"):
                for stmt in tx.rollback_plan.rollback_statements:
                    executor_ctx.execute_statement(stmt.sql)
            self.transition_state(tx, TransactionState.ROLLED_BACK)
        except Exception as e:
            self.transition_state(tx, TransactionState.FAILED)
            raise TransactionError(
                message=f"Rollback failed for transaction '{tx.tx_id}': {e}",
                cause=e,
                recovery_recommendation="Manual DBA intervention required to clean up partially rolled-back state."
            )
