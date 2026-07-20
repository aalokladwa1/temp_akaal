"""Canonical JSON Serialization & SHA-256 Checksum Utilities."""

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Produce deterministic canonical JSON string with sorted keys and no unnecessary whitespace."""
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    if isinstance(data, dict):
        # Exclude 'checksum' field if present to ensure consistent hashing
        data = {k: v for k, v in data.items() if k != "checksum"}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_sha256(payload: Any) -> str:
    """Compute SHA-256 hash of canonical JSON payload or string."""
    if isinstance(payload, str):
        content = payload
    else:
        content = canonical_json(payload)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_sha256(payload: Any, expected_checksum: str) -> bool:
    """Verify SHA-256 checksum match."""
    actual = compute_sha256(payload)
    return actual == expected_checksum
