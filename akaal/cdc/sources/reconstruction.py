"""
AKAAL CDC Engine Transaction Reconstruction & Buffer Flow Control.
====================================================================
Groups raw native database change events into ordered CDCTransaction objects,
enforces commit/rollback semantics, prevents cross-session/run contamination,
and integrates with P1 BackpressureController for resource safety.
"""

from typing import Dict, Any, List, Optional
import logging

from akaal.cdc.domain.events import (
    CDCEvent,
    CDCEventIdentity,
    CDCTransaction,
    CDCTransactionBoundary,
    CDCOperationType,
)
from akaal.cdc.domain.positions import CDCSourcePosition
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.streaming.domain.enums import BackpressureState

logger = logging.getLogger(__name__)


class TransactionReconstructor:
    """
    Reconstructs database-native transaction streams into canonical P3.1 CDCTransaction objects.
    - Guarantees events from different transactions never mix.
    - Guarantees uncommitted or rolled-back transactions are NEVER emitted as committed changes.
    - Uses P1 BackpressureController to prevent unbounded memory consumption.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        max_buffered_events: int = 1000,
        backpressure_controller: Optional[BackpressureController] = None,
    ) -> None:
        self.identity = identity
        self.max_buffered_events = max_buffered_events
        self.backpressure = backpressure_controller or BackpressureController(
            max_queue_capacity=max_buffered_events,
            high_watermark_ratio=0.8,
            low_watermark_ratio=0.2,
        )
        self.active_transactions: Dict[str, CDCTransaction] = {}
        self.committed_transactions: List[CDCTransaction] = []
        self.total_events_buffered = 0

    def process_native_record(
        self,
        tx_id: str,
        source_engine: str,
        source_database: str,
        source_schema: str,
        source_table: str,
        operation: CDCOperationType,
        position: CDCSourcePosition,
        boundary: CDCTransactionBoundary,
        before_image: Optional[Dict[str, Any]] = None,
        after_image: Optional[Dict[str, Any]] = None,
        commit_timestamp: Optional[str] = None,
    ) -> Optional[CDCTransaction]:
        """
        Processes a raw native change record. Returns CDCTransaction if record represents a COMMIT, otherwise returns None.
        """
        # Apply P1 Backpressure check
        bp_state = self.backpressure.check_and_update(self.total_events_buffered)
        if bp_state in (BackpressureState.HIGH_WATERMARK, BackpressureState.THROTTLED):
            logger.warning(f"[TRANSACTION RECONSTRUCTOR] Backpressure active ({bp_state.value}, {self.total_events_buffered} events buffered).")

        if boundary == CDCTransactionBoundary.ABORT:
            if tx_id in self.active_transactions:
                aborted_tx = self.active_transactions.pop(tx_id)
                self.total_events_buffered -= len(aborted_tx.events)
                aborted_tx.mark_abort()
                logger.info(f"[TRANSACTION RECONSTRUCTOR] Transaction '{tx_id}' rolled back. Discarded {len(aborted_tx.events)} events.")
            return None

        if tx_id not in self.active_transactions:
            self.active_transactions[tx_id] = CDCTransaction(
                tx_id=tx_id,
                identity=self.identity,
                commit_position=position,
                commit_timestamp=commit_timestamp,
            )

        tx = self.active_transactions[tx_id]

        if boundary == CDCTransactionBoundary.BEGIN:
            return None

        evt = CDCEvent(
            identity=self.identity,
            source_engine=source_engine,
            source_database=source_database,
            source_schema=source_schema,
            source_table=source_table,
            operation=operation,
            position=position,
            before_image=before_image,
            after_image=after_image,
            boundary=boundary,
            tx_id=tx_id,
            commit_timestamp=commit_timestamp,
        )
        tx.add_event(evt)
        self.total_events_buffered += 1

        if boundary in (CDCTransactionBoundary.COMMIT, CDCTransactionBoundary.SINGLE_EVENT):
            tx.commit_position = position
            tx.mark_commit()
            completed_tx = self.active_transactions.pop(tx_id)
            self.total_events_buffered -= len(completed_tx.events)
            self.committed_transactions.append(completed_tx)
            return completed_tx

        return None

    def pop_committed_transactions(self) -> List[CDCTransaction]:
        txs = self.committed_transactions
        self.committed_transactions = []
        return txs

    def clear(self) -> None:
        self.active_transactions.clear()
        self.committed_transactions.clear()
        self.total_events_buffered = 0
