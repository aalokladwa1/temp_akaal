"""
AKAAL Platform 5 — TransactionStore

Provides thread-safe persistence for SchemaTransaction lifecycle metadata.
"""

from typing import Dict, List, Optional
import threading

from akaal.schema.domain.identifiers import TransactionID
from akaal.schema.transactions.model import SchemaTransaction


class TransactionStore:
    """Thread-safe transaction store."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._tx_map: Dict[str, SchemaTransaction] = {}

    def save_transaction(self, tx: SchemaTransaction) -> None:
        with self._mutex:
            self._tx_map[str(tx.tx_id)] = tx

    def get_transaction(self, tx_id: TransactionID) -> Optional[SchemaTransaction]:
        with self._mutex:
            return self._tx_map.get(str(tx_id))

    def list_active_transactions(self) -> List[SchemaTransaction]:
        with self._mutex:
            return [tx for tx in self._tx_map.values() if tx.state not in (tx.state.COMMITTED, tx.state.ROLLED_BACK, tx.state.FAILED)]
