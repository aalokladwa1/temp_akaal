"""
Governance & Enterprise Audit Center.
Creates immutable, tamper-evident SHA-256 hash-chained operational audit records.
"""

from typing import Dict, List, Any
from threading import RLock
import hashlib
import json
import time


class OperationalAuditRecord:
    def __init__(self, record_id: str, actor: str, action: str, prev_hash: str, details: Dict[str, Any]) -> None:
        self.record_id = record_id
        self.actor = actor
        self.action = action
        self.timestamp = time.time()
        self.details = details
        self.prev_hash = prev_hash
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.record_id}:{self.actor}:{self.action}:{self.timestamp}:{self.prev_hash}:{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class GovernanceAuditCenter:
    """Manages immutable audit log chains."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._chain: List[OperationalAuditRecord] = []

    def record_action(self, actor: str, action: str, details: Dict[str, Any]) -> OperationalAuditRecord:
        with self._lock:
            prev_hash = self._chain[-1].hash if self._chain else "0" * 64
            rec_id = f"aud_{int(time.time() * 1000)}_{len(self._chain)}"
            rec = OperationalAuditRecord(rec_id, actor, action, prev_hash, details)
            self._chain.append(rec)
            return rec

    def verify_chain_integrity(self) -> bool:
        with self._lock:
            prev_hash = "0" * 64
            for rec in self._chain:
                if rec.prev_hash != prev_hash:
                    return False
                if rec.hash != rec._compute_hash():
                    return False
                prev_hash = rec.hash
            return True

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "record_id": r.record_id,
                    "actor": r.actor,
                    "action": r.action,
                    "timestamp": r.timestamp,
                    "hash": r.hash,
                    "prev_hash": r.prev_hash
                }
                for r in self._chain
            ]
