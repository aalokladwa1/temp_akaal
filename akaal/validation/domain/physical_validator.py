"""
AKAAL Validation Engine — Canonical Physical Checksum & Merkle Validator
========================================================================
High-performance database-row canonicalization, versioned length-prefixed framed
byte serialization (AKAAL-CANONICAL-V1), SHA-256 row hashing, LOB streaming,
and Merkle tree verification.
"""

from dataclasses import dataclass, field
import datetime
import decimal
import hashlib
import json
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import unicodedata
import uuid

from akaal.schema.domain.types import CanonicalType, CanonicalTypeCategory

logger = logging.getLogger("akaal.validation.domain.physical_validator")

SERIALIZATION_VERSION = "AKAAL-CANONICAL-V1"


class ValidationExecutionError(Exception):
    """Raised when physical database validation fails closed due to query or schema errors."""

    pass


@dataclass
class CanonicalValue:
    """Database-independent canonical value model for integrity verification."""

    type_category: CanonicalTypeCategory
    normalized_bytes: bytes
    is_null: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class CanonicalValueSerializer:
    """Universal Canonical Value Serializer (AKAAL-CANONICAL-V1)."""

    VERSION = SERIALIZATION_VERSION

    @classmethod
    def serialize_value(
        cls, val: Any, canonical_type: Optional[CanonicalType] = None, dialect: str = "ansi"
    ) -> bytes:
        """
        Database & Driver independent deterministic value serialization.
        Format: [TYPE_CAT_LEN]:[TYPE_CAT]:[NULL_FLAG]:[VAL_BYTES_LEN]:[VAL_BYTES]
        """
        if val is None:
            return b"TYPE:NULL:1:0:"

        # Oracle empty string is NULL
        if isinstance(val, str) and val == "" and dialect.lower() == "oracle":
            return b"TYPE:NULL:1:0:"

        # Category determination
        cat = canonical_type.category if canonical_type else cls._infer_category(val)

        # 1. NULL Handling
        if cat == CanonicalTypeCategory.UNKNOWN and val is None:
            return b"TYPE:NULL:1:0:"

        # 2. Boolean Handling
        if cat == CanonicalTypeCategory.BOOLEAN or isinstance(val, bool):
            b_val = b"1" if bool(val) else b"0"
            return f"TYPE:BOOL:0:{len(b_val)}:".encode("utf-8") + b_val

        # 3. Numeric / Decimal Handling
        if cat in (CanonicalTypeCategory.INTEGER, CanonicalTypeCategory.DECIMAL, CanonicalTypeCategory.FLOAT) or isinstance(
            val, (int, float, decimal.Decimal)
        ):
            if isinstance(val, float):
                # Handle special IEEE float values
                val_str = str(val)
                if val_str == "nan":
                    d_bytes = b"NaN"
                elif val_str == "inf":
                    d_bytes = b"+Infinity"
                elif val_str == "-inf":
                    d_bytes = b"-Infinity"
                else:
                    d_dec = decimal.Decimal(val_str)
                    raw_f = f"{d_dec:f}"
                    d_str = raw_f.rstrip("0").rstrip(".") if "." in raw_f else raw_f
                    d_bytes = d_str.encode("utf-8")
            else:
                d_dec = decimal.Decimal(val)
                raw_f = f"{d_dec:f}"
                d_str = raw_f.rstrip("0").rstrip(".") if "." in raw_f else raw_f
                d_bytes = d_str.encode("utf-8")

            return f"TYPE:NUM:0:{len(d_bytes)}:".encode("utf-8") + d_bytes

        # 4. Timestamp / Date Handling
        if cat in (CanonicalTypeCategory.DATE, CanonicalTypeCategory.TIME, CanonicalTypeCategory.TIMESTAMP, CanonicalTypeCategory.TIMESTAMPTZ) or isinstance(
            val, (datetime.datetime, datetime.date, datetime.time)
        ):
            if isinstance(val, datetime.datetime):
                if val.tzinfo is not None:
                    utc_dt = val.astimezone(datetime.timezone.utc)
                    dt_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    dt_str = val.strftime("%Y-%m-%dT%H:%M:%S.%f")
            elif isinstance(val, datetime.date):
                dt_str = val.strftime("%Y-%m-%d")
            else:
                dt_str = str(val)

            dt_bytes = dt_str.encode("utf-8")
            return f"TYPE:DATE:0:{len(dt_bytes)}:".encode("utf-8") + dt_bytes

        # 5. UUID Handling
        if cat == CanonicalTypeCategory.UUID or isinstance(val, uuid.UUID):
            u_obj = val if isinstance(val, uuid.UUID) else uuid.UUID(str(val))
            u_bytes = u_obj.bytes
            return f"TYPE:UUID:0:{len(u_bytes)}:".encode("utf-8") + u_bytes

        # 6. JSON / JSONB Key Ordering Normalization
        if cat in (CanonicalTypeCategory.JSON, CanonicalTypeCategory.JSONB) or isinstance(val, (dict, list)):
            if isinstance(val, str):
                try:
                    obj = json.loads(val)
                except Exception:
                    obj = val
            else:
                obj = val

            if isinstance(obj, (dict, list)):
                json_str = json.dumps(obj, sort_keys=True, separators=(",", ":"))
                j_bytes = json_str.encode("utf-8")
            else:
                j_bytes = str(val).encode("utf-8")

            return f"TYPE:JSON:0:{len(j_bytes)}:".encode("utf-8") + j_bytes

        # 7. Binary / BYTEA / VARBINARY
        if cat in (CanonicalTypeCategory.BINARY, CanonicalTypeCategory.VARBINARY, CanonicalTypeCategory.BLOB) or isinstance(
            val, (bytes, bytearray, memoryview)
        ):
            raw_bytes = bytes(val)
            return f"TYPE:BYTES:0:{len(raw_bytes)}:".encode("utf-8") + raw_bytes

        # 8. Text / UTF-8 String Normalization
        norm_str = unicodedata.normalize("NFC", str(val))
        str_bytes = norm_str.encode("utf-8")
        return f"TYPE:STR:0:{len(str_bytes)}:".encode("utf-8") + str_bytes

    @classmethod
    def _infer_category(cls, val: Any) -> CanonicalTypeCategory:
        if isinstance(val, bool):
            return CanonicalTypeCategory.BOOLEAN
        if isinstance(val, int):
            return CanonicalTypeCategory.INTEGER
        if isinstance(val, float):
            return CanonicalTypeCategory.FLOAT
        if isinstance(val, decimal.Decimal):
            return CanonicalTypeCategory.DECIMAL
        if isinstance(val, (datetime.datetime, datetime.date)):
            return CanonicalTypeCategory.TIMESTAMP
        if isinstance(val, (bytes, bytearray)):
            return CanonicalTypeCategory.BINARY
        if isinstance(val, uuid.UUID):
            return CanonicalTypeCategory.UUID
        if isinstance(val, (dict, list)):
            return CanonicalTypeCategory.JSON
        return CanonicalTypeCategory.VARCHAR


class PhysicalChecksumValidator:
    """
    Canonical Physical Database Checksum & Merkle Tree Validator.
    Normalizes native database values to AKAAL logical data types using
    length-prefixed framed byte serialization (AKAAL-CANONICAL-V1) and SHA-256 Merkle root verification.
    """

    SERIALIZATION_VERSION = SERIALIZATION_VERSION

    @classmethod
    def normalize_value_to_bytes(
        cls, val: Any, canonical_type: Optional[CanonicalType] = None, dialect: str = "ansi"
    ) -> bytes:
        """Database-independent deterministic value normalization."""
        return CanonicalValueSerializer.serialize_value(val, canonical_type=canonical_type, dialect=dialect)

    @classmethod
    def serialize_row(
        cls, row: Tuple[Any, ...], columns: List[str], dialect: str = "ansi"
    ) -> bytes:
        """
        Length-prefixed framed row serialization preventing delimiter collisions.
        Framing format: VERSION:AKAAL-CANONICAL-V1:[COL_NAME_LEN]:[COL_NAME]:[VAL_BYTES_LEN]:[VAL_BYTES]
        """
        buffer = bytearray(f"VERSION:{SERIALIZATION_VERSION}:".encode("utf-8"))
        for col_name, val in zip(columns, row):
            col_bytes = col_name.lower().encode("utf-8")
            val_bytes = cls.normalize_value_to_bytes(val, dialect=dialect)

            frame_header = (
                f"{len(col_bytes)}:".encode("utf-8")
                + col_bytes
                + f":{len(val_bytes)}:".encode("utf-8")
            )
            buffer.extend(frame_header)
            buffer.extend(val_bytes)

        return bytes(buffer)

    @classmethod
    def hash_row(cls, row: Tuple[Any, ...], columns: List[str], dialect: str = "ansi") -> str:
        """Computes SHA-256 hex digest for a single database row."""
        serialized = cls.serialize_row(row, columns, dialect=dialect)
        return hashlib.sha256(serialized).hexdigest()

    @classmethod
    def hash_lob_stream(cls, chunk_iterable: Iterable[bytes]) -> str:
        """Computes SHA-256 hex digest for a streaming LOB without loading the entire payload into RAM."""
        hasher = hashlib.sha256()
        for chunk in chunk_iterable:
            if chunk:
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def build_merkle_root(cls, row_hashes: List[str]) -> str:
        """
        Constructs Merkle tree root hash from a list of row hashes.
        Unordered rows are sorted deterministically if no primary key order is established.
        """
        if not row_hashes:
            return hashlib.sha256(f"EMPTY_TABLE:{SERIALIZATION_VERSION}".encode("utf-8")).hexdigest()

        current_level = list(row_hashes)

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = (left + right).encode("utf-8")
                next_level.append(hashlib.sha256(combined).hexdigest())
            current_level = next_level

        return current_level[0]

    def validate_table_checksums(
        self,
        source_rows: List[Tuple[Any, ...]],
        target_rows: List[Tuple[Any, ...]],
        columns: List[str],
        pk_columns: Optional[List[str]] = None,
        source_dialect: str = "oracle",
        target_dialect: str = "postgresql",
        validation_level: str = "CHECKSUM",
    ) -> Dict[str, Any]:
        """
        Executes physical validation comparison between source and target table rows.
        Returns detailed status, row counts, Merkle roots, and mismatched row indices.
        """
        source_count = len(source_rows)
        target_count = len(target_rows)

        if source_count != target_count:
            logger.error(f"[PHYSICAL VALIDATOR] Row count mismatch: Source={source_count}, Target={target_count}")
            return {
                "status": "FAILED",
                "reason": f"Row count mismatch: Source={source_count}, Target={target_count}",
                "source_count": source_count,
                "target_count": target_count,
                "mismatches": [],
                "serialization_version": SERIALIZATION_VERSION,
                "hash_algorithm": "SHA-256",
            }

        if validation_level.upper() == "ROW_COUNT":
            return {
                "status": "PASSED",
                "reason": "Row counts match",
                "source_count": source_count,
                "target_count": target_count,
                "mismatches": [],
                "serialization_version": SERIALIZATION_VERSION,
                "hash_algorithm": "SHA-256",
            }

        # Calculate Row SHA-256 Hashes
        source_hashes = [self.hash_row(r, columns, dialect=source_dialect) for r in source_rows]
        target_hashes = [self.hash_row(r, columns, dialect=target_dialect) for r in target_rows]

        # If no primary key ordering is defined, sort row hashes deterministically for set equality
        if not pk_columns:
            logger.info("[PHYSICAL VALIDATOR] No PK defined for table. Sorting row digests deterministically.")
            source_hashes_sorted = sorted(source_hashes)
            target_hashes_sorted = sorted(target_hashes)
        else:
            source_hashes_sorted = source_hashes
            target_hashes_sorted = target_hashes

        source_merkle_root = self.build_merkle_root(source_hashes_sorted)
        target_merkle_root = self.build_merkle_root(target_hashes_sorted)

        mismatches = []
        for idx, (s_h, t_h) in enumerate(zip(source_hashes_sorted, target_hashes_sorted)):
            if s_h != t_h:
                mismatches.append({
                    "row_index": idx,
                    "source_hash": s_h,
                    "target_hash": t_h,
                })

        evidence_payload = f"{source_count}:{source_merkle_root}:{target_merkle_root}:{SERIALIZATION_VERSION}"
        evidence_fingerprint = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

        if source_merkle_root != target_merkle_root or mismatches:
            logger.error(f"[PHYSICAL VALIDATOR] Merkle Root mismatch! Source={source_merkle_root}, Target={target_merkle_root}")
            return {
                "status": "FAILED",
                "reason": "Data digest mismatch",
                "source_count": source_count,
                "target_count": target_count,
                "source_merkle_root": source_merkle_root,
                "target_merkle_root": target_merkle_root,
                "mismatches": mismatches,
                "serialization_version": SERIALIZATION_VERSION,
                "hash_algorithm": "SHA-256",
                "evidence_fingerprint": evidence_fingerprint,
            }

        return {
            "status": "PASSED",
            "reason": "Data hashes & Merkle root match",
            "source_count": source_count,
            "target_count": target_count,
            "source_merkle_root": source_merkle_root,
            "target_merkle_root": target_merkle_root,
            "mismatches": [],
            "serialization_version": SERIALIZATION_VERSION,
            "hash_algorithm": "SHA-256",
            "evidence_fingerprint": evidence_fingerprint,
        }
