"""
Durable Queue Storage Models for Authority #5 — Durability.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class QueueMessageRef:
    """Reference handle for a stored durable queue message."""
    message_id: str
    queue_name: str
    sequence_number: int
    payload: bytes
    claimed_by: Optional[str] = None
    claim_id: Optional[str] = None
    lease_expires_at: Optional[str] = None
    attempt_count: int = 0
    created_at: str = ""


@dataclass(frozen=True)
class ClaimLeaseState:
    """Atomic queue message claim state."""
    message_id: str
    claimed: bool
    claimed_by: str
    claim_id: str
    lease_expires_at: str
