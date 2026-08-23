"""
State Integrity & Corruption Sanitizer for Authority #5 — Durability (DUR-011).
"""

import hashlib
import json
import zlib
from typing import Any, Dict, Optional
from akaalEngine.durability.models.errors import StateCorruptError, IntegrityFailureError


class StateIntegritySanitizer:
    """Computes and verifies cryptographic checksums across records and binary payloads."""

    @staticmethod
    def compute_dict_checksum(payload: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 over a state dictionary."""
        serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def verify_dict_checksum(payload: Dict[str, Any], expected_checksum: str) -> None:
        """Verifies dictionary checksum or raises StateCorruptError."""
        computed = StateIntegritySanitizer.compute_dict_checksum(payload)
        if computed != expected_checksum:
            raise StateCorruptError(f"Checksum mismatch: expected '{expected_checksum}', got '{computed}'.")

    @staticmethod
    def compute_binary_crc32(data: bytes) -> int:
        """Computes CRC32 checksum over raw binary data."""
        return zlib.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def compute_binary_sha256(data: bytes) -> str:
        """Computes SHA-256 digest over raw binary data."""
        return hashlib.sha256(data).hexdigest()
