"""
AKAAL Platform 5 — Immutable Operation Journal Store

Provides append-only storage for OperationRecord hash chains. The journal is the single source of truth.
"""

import threading
from typing import Dict, List, Optional

from akaal.schema.domain.errors import JournalIntegrityError
from akaal.schema.domain.identifiers import CheckpointID, OperationID
from akaal.schema.domain.journal import JournalChecksum, OperationRecord


class JournalStore:
    """Thread-safe append-only OperationJournal store."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._records: List[OperationRecord] = []
        self._op_map: Dict[str, OperationRecord] = {}
        self._last_hash: str = "0" * 64
        self._checkpoints: Dict[str, int] = {}  # checkpoint_id -> record index

    def append_record(self, record: OperationRecord) -> OperationRecord:
        with self._mutex:
            if not record.verify_integrity(self._last_hash):
                raise JournalIntegrityError(
                    message=f"Journal record '{record.operation_id}' failed cryptographic hash-chain verification.",
                    recovery_recommendation="Inspect journal store for unauthorized modification or corruption."
                )
            self._records.append(record)
            self._op_map[str(record.operation_id)] = record
            if record.checksum:
                self._last_hash = record.checksum.hash_value
            return record

    def get_records_from(self, start_index: int = 0) -> List[OperationRecord]:
        with self._mutex:
            return list(self._records[start_index:])

    def create_checkpoint(self) -> CheckpointID:
        with self._mutex:
            chk_id = CheckpointID.generate()
            self._checkpoints[str(chk_id)] = len(self._records)
            return chk_id

    def get_checkpoint_index(self, chk_id: CheckpointID) -> int:
        with self._mutex:
            return self._checkpoints.get(str(chk_id), 0)

    def count(self) -> int:
        with self._mutex:
            return len(self._records)
