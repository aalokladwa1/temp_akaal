"""
AKAAL Platform 6 — Cryptographic Ledger Block Definition.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Dict, Any


@dataclass(frozen=True)
class LedgerBlock:
    index: int
    timestamp: str
    previous_hash: str
    decision_data: Dict[str, Any]
    hash: str

    @staticmethod
    def calculate_hash(index: int, timestamp: str, previous_hash: str, decision_data: Dict[str, Any]) -> str:
        serialized = json.dumps(decision_data, sort_keys=True)
        raw_payload = f"{index}|{timestamp}|{previous_hash}|{serialized}"
        return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()
