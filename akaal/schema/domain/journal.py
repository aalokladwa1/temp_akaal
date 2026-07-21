"""
AKAAL Platform 5 — Immutable Operation Journal Domain Models

Defines tamper-evident, hash-chained OperationRecord structures for DDL replay and auditing.
"""

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from akaal.schema.domain.enums import ReplayStatus
from akaal.schema.domain.identifiers import OperationID, TransactionID


@dataclass
class JournalChecksum:
    hash_value: str

    @classmethod
    def compute(cls, payload: Dict[str, Any], previous_hash: str = "0" * 64) -> "JournalChecksum":
        canonical_str = json.dumps(payload, sort_keys=True)
        combined = f"{previous_hash}:{canonical_str}"
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return cls(hash_value=digest)


@dataclass
class OperationRecord:
    operation_id: OperationID
    tx_id: TransactionID
    change_payload: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    previous_hash: str = field(default="0" * 64)
    checksum: Optional[JournalChecksum] = None
    replay_status: ReplayStatus = field(default=ReplayStatus.UNEXECUTED)
    timestamp: float = field(default_factory=time.time)
    audit_metadata: Dict[str, Any] = field(default_factory=dict)
    execution_duration_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.checksum is None:
            payload = {
                "op_id": str(self.operation_id),
                "tx_id": str(self.tx_id),
                "change_payload": self.change_payload,
                "dependencies": self.dependencies,
                "timestamp": self.timestamp,
            }
            self.checksum = JournalChecksum.compute(payload, self.previous_hash)

    def verify_integrity(self, expected_previous_hash: str) -> bool:
        if self.previous_hash != expected_previous_hash:
            return False
        payload = {
            "op_id": str(self.operation_id),
            "tx_id": str(self.tx_id),
            "change_payload": self.change_payload,
            "dependencies": self.dependencies,
            "timestamp": self.timestamp,
        }
        recomputed = JournalChecksum.compute(payload, self.previous_hash)
        return self.checksum is not None and recomputed.hash_value == self.checksum.hash_value
