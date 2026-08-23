"""
akaalEngine.evidence.canonical
==============================
Deterministic canonical serialization and cryptographic SHA-256 digest computation for Authority #12.
Guarantees identical byte representations for identical evidence structures regardless of key insertion order
or non-semantic manifest artifact sequence.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Union

from akaalEngine.evidence.models.artifact import EvidenceDigest


class CanonicalEvidenceSerializer:
    """
    Produces deterministic UTF-8 JSON representations of evidence payloads.
    Alphabetically sorts object keys, sorts non-semantic manifest artifacts by artifact_id,
    formats decimals/dates consistently, and enforces uniform byte representation.
    """

    @classmethod
    def serialize_to_dict(cls, data: Any) -> Any:
        """Recursively normalizes data structures into canonical primitive dicts/lists."""
        if data is None:
            return None
        if isinstance(data, Enum):
            return data.value
        if hasattr(data, "to_dict") and callable(data.to_dict):
            raw = data.to_dict(include_digest=False) if "include_digest" in data.to_dict.__code__.co_varnames else data.to_dict()
            return cls.serialize_to_dict(raw)
        if isinstance(data, dict):
            res_dict = {}
            for k, v in sorted(data.items(), key=lambda item: str(item[0])):
                if k == "artifacts" and isinstance(v, list):
                    # Sort manifest artifacts by artifact_id for NON-SEMANTIC manifest equality
                    sorted_artifacts = sorted(v, key=lambda art: art.get("artifact_id", "") if isinstance(art, dict) else (art.artifact_id if hasattr(art, "artifact_id") else str(art)))
                    res_dict[k] = [cls.serialize_to_dict(item) for item in sorted_artifacts]
                else:
                    res_dict[k] = cls.serialize_to_dict(v)
            return res_dict
        if isinstance(data, (list, tuple)):
            return [cls.serialize_to_dict(item) for item in data]
        if isinstance(data, Decimal):
            return str(data)
        if isinstance(data, (datetime, date)):
            return data.isoformat()
        if isinstance(data, (bytes, bytearray)):
            return data.hex()
        return data

    @classmethod
    def serialize_to_bytes(cls, data: Any) -> bytes:
        """Encodes normalized evidence payload into deterministic UTF-8 bytes."""
        normalized = cls.serialize_to_dict(data)
        json_str = json.dumps(
            normalized,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return json_str.encode("utf-8")


class EvidenceDigestCalculator:
    """
    Computes cryptographic SHA-256 digests over canonical evidence bytes.
    """

    @classmethod
    def compute_digest(cls, data: Any) -> EvidenceDigest:
        raw_bytes = CanonicalEvidenceSerializer.serialize_to_bytes(data)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        return EvidenceDigest(
            algorithm="SHA-256",
            canonical_bytes_len=len(raw_bytes),
            digest_hex=sha256,
            digital_signature_supported=False,
            digital_signature_status="DIGEST_INTEGRITY_ONLY",
        )
