"""
Execution Manifest Models for Authority #5 — Durability (DUR-014).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class ExecutionManifest:
    """Immutable execution identity manifest snapshot."""
    manifest_id: str
    migration_id: str
    config_hash: str
    discovery_hash: str
    schema_hash: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    checksum: Optional[str] = None
