"""
AKAAL Platform 6 — Immutable Cryptographic Decision Ledger.
"""

from typing import List, Dict, Any
import datetime
from akaal.governance.ledger.block import LedgerBlock
from akaal.governance.domain.exceptions import LedgerTamperError


class ImmutableDecisionLedger:
    """Append-only cryptographic hash-chained decision ledger supporting anti-tamper verification."""

    def __init__(self) -> None:
        self._chain: List[LedgerBlock] = []
        # Create Genesis Block
        genesis_time = "2026-01-01T00:00:00Z"
        genesis_data = {"event": "GENESIS_DECISION_LEDGER_BLOCK"}
        genesis_hash = LedgerBlock.calculate_hash(0, genesis_time, "0" * 64, genesis_data)
        genesis_block = LedgerBlock(
            index=0,
            timestamp=genesis_time,
            previous_hash="0" * 64,
            decision_data=genesis_data,
            hash=genesis_hash,
        )
        self._chain.append(genesis_block)

    def append_decision(self, decision_data: Dict[str, Any]) -> LedgerBlock:
        prev_block = self._chain[-1]
        index = prev_block.index + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        previous_hash = prev_block.hash

        block_hash = LedgerBlock.calculate_hash(index, timestamp, previous_hash, decision_data)
        block = LedgerBlock(
            index=index,
            timestamp=timestamp,
            previous_hash=previous_hash,
            decision_data=decision_data,
            hash=block_hash,
        )
        self._chain.append(block)
        return block

    def verify_integrity(self) -> bool:
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            prev = self._chain[i - 1]

            if current.previous_hash != prev.hash:
                raise LedgerTamperError(f"Ledger hash chain broken at index {i}: previous_hash mismatch.")

            recalculated = LedgerBlock.calculate_hash(
                current.index, current.timestamp, current.previous_hash, current.decision_data
            )
            if current.hash != recalculated:
                raise LedgerTamperError(f"Ledger block tampered at index {i}: hash recalculation mismatch.")

        return True

    def get_chain(self) -> List[LedgerBlock]:
        return list(self._chain)
