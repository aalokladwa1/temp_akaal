"""
AKAAL Platform 11 — Immutable Validation Ledger (SHA-256 Hash Chain).
"""

from typing import List, Dict, Any
import datetime
import hashlib
import json
from akaal.trust_certification.domain.models import ValidationLedgerEntry


class ImmutableValidationLedger:
    """Cryptographic hash-chained immutable audit ledger for migration proof."""

    def __init__(self) -> None:
        self._chain: List[ValidationLedgerEntry] = []
        genesis_time = "2026-01-01T00:00:00Z"
        genesis_payload = {"event": "GENESIS_TRUST_CERTIFICATION_BLOCK"}
        genesis_hash = self._calc_hash(0, genesis_time, "0" * 64, genesis_payload)
        genesis_entry = ValidationLedgerEntry(
            entry_id="val-block-0",
            index=0,
            timestamp=genesis_time,
            previous_hash="0" * 64,
            validation_payload=genesis_payload,
            block_hash=genesis_hash,
        )
        self._chain.append(genesis_entry)

    def _calc_hash(self, index: int, timestamp: str, prev_hash: str, payload: Dict[str, Any]) -> str:
        ser = json.dumps(payload, sort_keys=True)
        raw = f"{index}|{timestamp}|{prev_hash}|{ser}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def record_validation(self, payload: Dict[str, Any]) -> ValidationLedgerEntry:
        prev = self._chain[-1]
        idx = prev.index + 1
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        block_hash = self._calc_hash(idx, now, prev.block_hash, payload)

        entry = ValidationLedgerEntry(
            entry_id=f"val-block-{idx}",
            index=idx,
            timestamp=now,
            previous_hash=prev.block_hash,
            validation_payload=payload,
            block_hash=block_hash,
        )
        self._chain.append(entry)
        return entry

    def verify_chain(self) -> bool:
        for i in range(1, len(self._chain)):
            curr = self._chain[i]
            prev = self._chain[i - 1]
            if curr.previous_hash != prev.block_hash:
                return False
            recalc = self._calc_hash(curr.index, curr.timestamp, curr.previous_hash, curr.validation_payload)
            if curr.block_hash != recalc:
                return False
        return True
