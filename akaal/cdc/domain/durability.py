"""
AKAAL CDC Engine Durability Contracts & Checkpointing Models.
============================================================
Defines durable CDC checkpoint artifacts with cryptographic HMAC hashes and identity binding.
"""

from typing import Dict, Any, Optional
import datetime
import hashlib
import json

from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position


class CDCCheckpoint:
    """
    Durable CDC Checkpoint artifact binding:
    - migration_id, job_id, run_id, cdc_session_id, fencing_epoch
    - captured_position, applied_position, acknowledged_position
    - SHA-256 HMAC integrity fingerprint preventing checkpoint corruption/substitution.
    """

    def __init__(
        self,
        checkpoint_id: str,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        fencing_epoch: int,
        source_position: CDCSourcePosition,
        applied_position: Optional[CDCSourcePosition] = None,
        acknowledged_position: Optional[CDCSourcePosition] = None,
        created_at: Optional[str] = None,
        checkpoint_hash: Optional[str] = None,
    ) -> None:
        self.checkpoint_id = checkpoint_id
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.cdc_session_id = cdc_session_id
        self.fencing_epoch = fencing_epoch
        self.source_position = source_position
        self.applied_position = applied_position or source_position
        self.acknowledged_position = acknowledged_position or source_position
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.checkpoint_hash = checkpoint_hash or self.compute_hash()

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 hash of checkpoint identity and positions."""
        raw = f"{self.checkpoint_id}:{self.migration_id}:{self.job_id}:{self.run_id}:{self.cdc_session_id}:{self.fencing_epoch}:{self.source_position.to_string()}:{self.applied_position.to_string()}:{self.acknowledged_position.to_string()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Returns True if checkpoint hash matches computed hash."""
        return self.checkpoint_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "migration_id": self.migration_id,
            "job_id": self.job_id,
            "run_id": self.run_id,
            "cdc_session_id": self.cdc_session_id,
            "fencing_epoch": self.fencing_epoch,
            "source_position": self.source_position.to_dict(),
            "applied_position": self.applied_position.to_dict(),
            "acknowledged_position": self.acknowledged_position.to_dict(),
            "created_at": self.created_at,
            "checkpoint_hash": self.checkpoint_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCCheckpoint":
        chk = cls(
            checkpoint_id=data["checkpoint_id"],
            migration_id=data["migration_id"],
            job_id=data["job_id"],
            run_id=data["run_id"],
            cdc_session_id=data["cdc_session_id"],
            fencing_epoch=data["fencing_epoch"],
            source_position=parse_source_position(data["source_position"]),
            applied_position=parse_source_position(data["applied_position"]) if data.get("applied_position") else None,
            acknowledged_position=parse_source_position(data["acknowledged_position"]) if data.get("acknowledged_position") else None,
            created_at=data.get("created_at"),
            checkpoint_hash=data.get("checkpoint_hash"),
        )
        if not chk.verify_integrity():
            raise ValueError(f"[CORRUPT CHECKPOINT] Checkpoint '{chk.checkpoint_id}' failed SHA-256 integrity verification!")
        return chk


class CDCDurabilityContract:
    """Defines persistent vs volatile CDC state rules."""

    @staticmethod
    def is_durable_field(field_name: str) -> bool:
        DURABLE_FIELDS = {
            "migration_id",
            "job_id",
            "run_id",
            "cdc_session_id",
            "consistency_boundary",
            "initial_load_snapshot_position",
            "last_durably_captured_position",
            "last_durably_applied_position",
            "last_acknowledged_position",
            "fencing_epoch",
            "checkpoint_hash",
        }
        return field_name in DURABLE_FIELDS
