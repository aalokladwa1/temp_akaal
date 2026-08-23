"""
State Models for Authority #5 — Durability.
"""

from dataclasses import dataclass, field
import datetime
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class StateVersion:
    """Immutable state version handle."""
    key: str
    namespace: str
    version: int
    checksum: str
    updated_at: str


@dataclass(frozen=True)
class StateRecord:
    """Canonical persistent state record."""
    key: str
    namespace: str
    payload: Dict[str, Any]
    version: int = 1
    state_schema_version: int = 1
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    checksum: Optional[str] = None

    def with_version(self, new_version: int, new_checksum: str, updated_time: str) -> "StateRecord":
        return StateRecord(
            key=self.key,
            namespace=self.namespace,
            payload=dict(self.payload),
            version=new_version,
            state_schema_version=self.state_schema_version,
            created_at=self.created_at or updated_time,
            updated_at=updated_time,
            checksum=new_checksum,
        )


@dataclass(frozen=True)
class DurabilityConfig:
    """Durability Authority configuration parameters.

    Key material fields are required and installation-specific. There are no defaults.
    The authority fails closed at construction time if either is missing or empty.
    Keys are held only in process memory — they are never written to durable storage.
    """
    storage_dir: str
    fencing_signing_key: bytes = field(repr=False, compare=False)  # required — externally supplied secret
    journal_anchor_key: bytes = field(repr=False, compare=False)   # required — domain-separated secret key

    db_name: str = "durability.db"
    synchronous_mode: str = "NORMAL"    # FULL, NORMAL, OFF
    busy_timeout_sec: float = 30.0
    spill_quota_bytes: int = 10 * 1024 * 1024 * 1024  # 10 GB
    disk_reserve_bytes: int = 500 * 1024 * 1024        # 500 MB
    max_journal_retention_days: int = 30
    auto_compact_records: int = 100000

    def __post_init__(self) -> None:
        from akaalEngine.durability.models.errors import DurabilityConfigError
        if not self.fencing_signing_key or not isinstance(self.fencing_signing_key, bytes):
            raise DurabilityConfigError("DurabilityConfig requires non-empty bytes 'fencing_signing_key'.")
        if not self.journal_anchor_key or not isinstance(self.journal_anchor_key, bytes):
            raise DurabilityConfigError("DurabilityConfig requires non-empty bytes 'journal_anchor_key'.")
        if self.fencing_signing_key == self.journal_anchor_key:
            raise DurabilityConfigError("fencing_signing_key and journal_anchor_key must be domain-separated (distinct keys).")


