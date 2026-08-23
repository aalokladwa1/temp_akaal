"""
akaalEngine.transport.models.checkpoint
========================================
Resource- and strategy-bound TransportCheckpoint identity engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, Optional

from akaalEngine.transport.models.errors import (
    TransportCheckpointIdentityError,
    TransportCheckpointStaleError,
)


@dataclass(frozen=True)
class TransportCheckpoint:
    """
    Hardened TransportCheckpoint identity model.
    Binds source URI, target URI, schema fingerprint, partition strategy, and processing plan hash.
    """
    source_identity: str
    source_resource_version: str
    target_identity: str
    logical_object_name: str
    schema_fingerprint: str
    partition_id: str
    partition_strategy_fingerprint: str
    processing_plan_fingerprint: str
    transport_strategy_identity: str
    read_position: Optional[str] = None
    processed_position: Optional[str] = None
    write_position: Optional[str] = None
    committed_position: Optional[str] = None
    generation: int = 1
    identity_hash: str = ""

    def __post_init__(self) -> None:
        if not self.identity_hash:
            raw_data = {
                "source_identity": self.source_identity,
                "source_resource_version": self.source_resource_version,
                "target_identity": self.target_identity,
                "logical_object_name": self.logical_object_name,
                "schema_fingerprint": self.schema_fingerprint,
                "partition_id": self.partition_id,
                "partition_strategy_fingerprint": self.partition_strategy_fingerprint,
                "processing_plan_fingerprint": self.processing_plan_fingerprint,
                "transport_strategy_identity": self.transport_strategy_identity,
            }
            h = hashlib.sha256(json.dumps(raw_data, sort_keys=True).encode("utf-8")).hexdigest()
            object.__setattr__(self, "identity_hash", h)

    def validate_compatibility(self, expected_checkpoint: TransportCheckpoint) -> None:
        """Validates identity fingerprint compatibility. Raises TransportCheckpointIdentityError if mismatched."""
        if self.identity_hash != expected_checkpoint.identity_hash:
            raise TransportCheckpointIdentityError(
                f"Checkpoint identity mismatch! Expected '{expected_checkpoint.identity_hash}', got '{self.identity_hash}'"
            )
        if self.generation < expected_checkpoint.generation:
            raise TransportCheckpointStaleError(
                f"Checkpoint generation is stale! Current={self.generation}, expected >= {expected_checkpoint.generation}"
            )
