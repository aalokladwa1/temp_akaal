"""
AKAAL Platform 5 — SchemaSnapshot Engine

Provides immutable schema snapshots with SHA-256 integrity checksums and optional compression.
"""

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Dict, List, Optional
import zlib

from akaal.schema.domain.identifiers import SnapshotID, VersionID


@dataclass
class SchemaSnapshot:
    snapshot_id: SnapshotID
    version_id: VersionID
    tables: Dict[str, Any] = field(default_factory=dict)
    views: Dict[str, Any] = field(default_factory=dict)
    sequences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = field(default="")
    compressed_bytes: Optional[bytes] = None
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self.compute_checksum()

    def compute_checksum(self) -> str:
        payload = {
            "snap_id": str(self.snapshot_id),
            "ver_id": str(self.version_id),
            "tables": self.tables,
            "views": self.views,
            "sequences": self.sequences,
            "metadata": self.metadata,
        }
        raw_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        return self.checksum == self.compute_checksum()

    def compress(self) -> bytes:
        payload = {
            "snapshot_id": str(self.snapshot_id),
            "version_id": str(self.version_id),
            "tables": self.tables,
            "views": self.views,
            "sequences": self.sequences,
            "metadata": self.metadata,
            "checksum": self.checksum,
        }
        raw = json.dumps(payload).encode("utf-8")
        self.compressed_bytes = zlib.compress(raw)
        return self.compressed_bytes

    @classmethod
    def decompress(cls, data: bytes) -> "SchemaSnapshot":
        raw = zlib.decompress(data)
        payload = json.loads(raw.decode("utf-8"))
        return cls(
            snapshot_id=SnapshotID(payload["snapshot_id"]),
            version_id=VersionID(payload["version_id"]),
            tables=payload["tables"],
            views=payload["views"],
            sequences=payload["sequences"],
            metadata=payload["metadata"],
            checksum=payload["checksum"],
        )
