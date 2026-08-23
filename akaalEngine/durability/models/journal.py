"""
Operation Journal Models for Authority #5 — Durability.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class OperationRecord:
    """Immutable append-only operation record."""
    operation_id: str
    sequence_number: int
    operation_type: str
    payload: Dict[str, Any]
    payload_hash: str
    parent_hash: str
    checksum: str
    created_at: str


@dataclass(frozen=True)
class JournalBatch:
    """Batch of operation records for atomic append."""
    batch_id: str
    records: tuple[OperationRecord, ...]
    start_sequence: int
    end_sequence: int
