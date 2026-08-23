"""
akaalEngine.cdc.decode.transaction
==================================
TransactionReconstructionEngine grouping raw change events into CDCTransactions and preserving ACID global commit ordering.
"""

from typing import Dict, List, Optional

from akaalEngine.cdc.models.event import ChangeEvent, TransactionContext
from akaalEngine.cdc.models.transaction import CDCTransaction


class TransactionReconstructionEngine:
    """Buffers stream events by tx_id and emits fully committed CDCTransactions in strict global commit order."""

    def __init__(self) -> None:
        self._active_txs: Dict[str, CDCTransaction] = {}
        self._committed_queue: List[CDCTransaction] = []

    def process_event(self, event: ChangeEvent) -> Optional[CDCTransaction]:
        """
        Ingests a change event.
        When a transaction completes, it is placed in the global commit queue.
        Emits the next ready transaction in strict global commit order (only when no earlier active transaction is in-flight).
        """
        if not event.tx_context:
            tx_ctx = TransactionContext(tx_id=f"tx-single-{event.event_id}", commit_timestamp_iso=str(event.commit_timestamp), sequence_number=1)
            tx = CDCTransaction(tx_context=tx_ctx, events=[event], is_committed=True)
            return tx

        tx_id = event.tx_context.tx_id
        if tx_id not in self._active_txs:
            self._active_txs[tx_id] = CDCTransaction(tx_context=event.tx_context)

        tx = self._active_txs[tx_id]
        tx.add_event(event)

        if tx.tx_context.total_events_in_tx and len(tx.events) >= tx.tx_context.total_events_in_tx:
            tx.mark_committed()
            del self._active_txs[tx_id]
            self._committed_queue.append(tx)
            # Sort committed queue by global commit position / commit timestamp
            self._committed_queue.sort(key=lambda t: (t.events[0].commit_position if t.events else "", t.tx_context.commit_timestamp_iso))

            # Emit only if no active in-flight transaction has an earlier commit position / timestamp
            min_active_pos = min(
                (t.events[0].commit_position for t in self._active_txs.values() if t.events),
                default=None
            )
            head = self._committed_queue[0]
            head_pos = head.events[0].commit_position if head.events else ""

            if min_active_pos is None or head_pos <= min_active_pos:
                return self._committed_queue.pop(0)

        return None

    def flush_committed_in_order(self) -> List[CDCTransaction]:
        """Flushes all completed transactions in strict global commit order."""
        out = sorted(self._committed_queue, key=lambda t: (t.events[0].commit_position if t.events else "", t.tx_context.commit_timestamp_iso))
        self._committed_queue.clear()
        return out
