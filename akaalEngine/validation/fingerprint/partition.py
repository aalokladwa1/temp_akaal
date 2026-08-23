"""
akaalEngine.validation.fingerprint.partition
============================================
PartitionFingerprintEngine for Authority #11 (VAL-022, VAL-023, VAL-036).
Aggregates deterministic row fingerprints across bounded partition batches using order-independent hash combinations.
"""

import hashlib
from typing import Any, Dict, Iterable, List, Optional

from akaalEngine.validation.fingerprint.row import DeterministicRowFingerprinter


class PartitionFingerprintEngine:
    """
    Computes aggregated partition fingerprints over bounded row streams.
    Memory usage is strictly bounded by batch size (O(1) RAM w.r.t total rows).
    """

    def __init__(self, partition_id: str) -> None:
        self.partition_id = partition_id
        self.row_count = 0
        self._accumulator = 0  # XOR hash accumulator for order-independent partition aggregation

    def update_batch(self, rows: Iterable[Dict[str, Any]], column_names: Optional[List[str]] = None) -> None:
        """Updates partition fingerprint with a bounded batch of rows."""
        for row in rows:
            row_fp = DeterministicRowFingerprinter.compute_fingerprint(row, column_names=column_names)
            # Convert 64-char hex SHA-256 to 256-bit integer for XOR accumulation
            row_int = int(row_fp, 16)
            self._accumulator ^= row_int
            self.row_count += 1

    def finalize(self) -> str:
        """Finalizes partition fingerprint into a canonical 64-character SHA-256 hex string."""
        if self.row_count == 0:
            return hashlib.sha256(f"EMPTY_PARTITION_{self.partition_id}".encode("utf-8")).hexdigest()

        # Combine row_count with XOR accumulator to prevent count-canceling collisions
        final_str = f"COUNT:{self.row_count}#ACCUM:{self._accumulator:064x}"
        return hashlib.sha256(final_str.encode("utf-8")).hexdigest()
