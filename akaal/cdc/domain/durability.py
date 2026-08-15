"""
AKAAL CDC Engine Durability Contracts & Cryptographic HMAC Checkpointing Models.
===============================================================================
Defines durable CDC checkpoint artifacts with keyed SHA-256 HMAC integrity hashes and identity binding.
"""

from typing import Dict, Any, Optional
import datetime
import hmac
import hashlib
import json
import os

from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position


class CDCKeyProvider:
    """System HMAC Key Provider for cryptographic CDC checkpoint integrity."""

    _SYSTEM_KEY: str = "AKAAL-CANONICAL-CDC-HMAC-SECRET-KEY-V1"

    @classmethod
    def get_checkpoint_hmac_key(cls) -> bytes:
        env_key = os.environ.get("AKAAL_CDC_HMAC_KEY")
        if env_key:
            return env_key.encode("utf-8")
        return cls._SYSTEM_KEY.encode("utf-8")


class CDCCheckpoint:
    """
    Durable CDC Checkpoint artifact binding:
    - migration_id, job_id, run_id, cdc_session_id, fencing_epoch
    - captured_position, applied_position, acknowledged_position
    - Keyed SHA-256 HMAC integrity fingerprint preventing checkpoint corruption, forgery, or substitution.
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
        secret_key: Optional[bytes] = None,
    ) -> None:
        if not checkpoint_id or not migration_id or not job_id or not run_id or not cdc_session_id:
            raise ValueError("All checkpoint identity fields (checkpoint_id, migration_id, job_id, run_id, cdc_session_id) must be non-empty.")
        if fencing_epoch < 0:
            raise ValueError("fencing_epoch must be a non-negative integer.")

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

        # Enforce position safety invariants: acknowledged <= applied <= captured
        if self.applied_position.is_after(self.source_position):
            raise ValueError(f"[CHECKPOINT CONTRADICTION] Applied position {self.applied_position} cannot exceed source captured position {self.source_position}.")
        if self.acknowledged_position.is_after(self.applied_position):
            raise ValueError(f"[CHECKPOINT CONTRADICTION] Acknowledged position {self.acknowledged_position} cannot exceed applied position {self.applied_position}.")

        self.secret_key = secret_key or CDCKeyProvider.get_checkpoint_hmac_key()
        self.checkpoint_hash = checkpoint_hash or self.compute_hmac(self.secret_key)

    def compute_hmac(self, key: Optional[bytes] = None) -> str:
        """Computes deterministic Keyed SHA-256 HMAC digest of checkpoint identity and positions."""
        hmac_key = key or self.secret_key or CDCKeyProvider.get_checkpoint_hmac_key()
        raw = f"{self.checkpoint_id}:{self.migration_id}:{self.job_id}:{self.run_id}:{self.cdc_session_id}:{self.fencing_epoch}:{self.source_position.to_string()}:{self.applied_position.to_string()}:{self.acknowledged_position.to_string()}"
        return hmac.new(hmac_key, raw.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_integrity(self, key: Optional[bytes] = None) -> bool:
        """Returns True if checkpoint_hash matches computed HMAC digest."""
        expected = self.compute_hmac(key)
        return hmac.compare_digest(self.checkpoint_hash, expected)

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
    def from_dict(cls, data: Dict[str, Any], key: Optional[bytes] = None) -> "CDCCheckpoint":
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
            secret_key=key,
        )
        if not chk.verify_integrity(key):
            raise ValueError(f"[CORRUPT CHECKPOINT] Checkpoint '{chk.checkpoint_id}' failed SHA-256 HMAC integrity verification!")
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
