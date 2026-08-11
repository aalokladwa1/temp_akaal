"""
AKAAL Validation Engine — Canonical Physical Checksum & Merkle Validator
========================================================================
High-performance database-row canonicalization, deterministic length-prefixed framed
serialization, SHA-256 row hashing, and Merkle tree verification.
"""

import hashlib
import decimal
import datetime
import unicodedata
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("akaal.validation.domain.physical_validator")


class ValidationExecutionError(Exception):
    """Raised when physical database validation fails closed due to query or schema errors."""
    pass


class PhysicalChecksumValidator:
    """
    Canonical Physical Database Checksum & Merkle Tree Validator.
    Normalizes native database values to AKAAL logical data types using
    length-prefixed framed byte serialization and SHA-256 Merkle root verification.
    """

    @staticmethod
    def normalize_value_to_bytes(val: Any, dialect: str = "ansi") -> bytes:
        """
        Database-independent deterministic value normalization.
        """
        # NULL & Empty String Handling
        if val is None:
            return b"TYPE:NULL"

        if isinstance(val, str):
            # Oracle treats empty strings as NULL
            if val == "":
                if dialect.lower() == "oracle":
                    return b"TYPE:NULL"
                else:
                    return b"TYPE:STR:0:"

            # String Unicode NFC Normalization
            norm_str = unicodedata.normalize("NFC", val)
            encoded = norm_str.encode("utf-8")
            return f"TYPE:STR:{len(encoded)}:".encode("utf-8") + encoded

        # Boolean Handling
        if isinstance(val, bool):
            return b"TYPE:BOOL:1" if val else b"TYPE:BOOL:0"

        # Exact Numeric / Decimal Handling (No float conversion)
        if isinstance(val, (int, float, decimal.Decimal)):
            if isinstance(val, float):
                # Format float deterministically without trailing zeroes
                d_val = decimal.Decimal(str(val))
            else:
                d_val = decimal.Decimal(val)

            # Strip trailing zeroes for non-zero decimals
            normalized_d = d_val.normalize()
            d_str = str(normalized_d)
            if "E" in d_str or "e" in d_str:
                d_str = f"{normalized_d:f}"

            encoded = d_str.encode("utf-8")
            return f"TYPE:DEC:{len(encoded)}:".encode("utf-8") + encoded

        # Timestamp / Date Handling
        if isinstance(val, (datetime.datetime, datetime.date)):
            if isinstance(val, datetime.datetime):
                if val.tzinfo is not None:
                    # Convert tz-aware to UTC ISO-8601
                    utc_dt = val.astimezone(datetime.timezone.utc)
                    iso_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    # Preserve tz-naive precision
                    iso_str = val.strftime("%Y-%m-%dT%H:%M:%S.%f")
            else:
                iso_str = val.strftime("%Y-%m-%d")

            encoded = iso_str.encode("utf-8")
            return f"TYPE:DATE:{len(encoded)}:".encode("utf-8") + encoded

        # Binary / BYTEA / RAW Handling
        if isinstance(val, (bytes, bytearray, memoryview)):
            raw_bytes = bytes(val)
            return f"TYPE:BYTES:{len(raw_bytes)}:".encode("utf-8") + raw_bytes

        # Fallback String Encoding
        fallback_str = unicodedata.normalize("NFC", str(val))
        encoded = fallback_str.encode("utf-8")
        return f"TYPE:STR:{len(encoded)}:".encode("utf-8") + encoded

    @classmethod
    def serialize_row(cls, row: Tuple[Any, ...], columns: List[str], dialect: str = "ansi") -> bytes:
        """
        Length-prefixed framed serialization preventing delimiter collisions.
        Framing format: [COL_NAME_LEN]:[COL_NAME]:[VAL_BYTES_LEN]:[VAL_BYTES]
        """
        buffer = bytearray()
        for col_name, val in zip(columns, row):
            col_bytes = col_name.lower().encode("utf-8")
            val_bytes = cls.normalize_value_to_bytes(val, dialect=dialect)

            frame_header = f"{len(col_bytes)}:".encode("utf-8") + col_bytes + f":{len(val_bytes)}:".encode("utf-8")
            buffer.extend(frame_header)
            buffer.extend(val_bytes)

        return bytes(buffer)

    @classmethod
    def hash_row(cls, row: Tuple[Any, ...], columns: List[str], dialect: str = "ansi") -> str:
        """Computes SHA-256 hex digest for a single database row."""
        serialized = cls.serialize_row(row, columns, dialect=dialect)
        return hashlib.sha256(serialized).hexdigest()

    @classmethod
    def build_merkle_root(cls, row_hashes: List[str]) -> str:
        """
        Constructs Merkle tree root hash from a list of row hashes.
        Unordered rows are sorted deterministically if no primary key order is established.
        """
        if not row_hashes:
            return hashlib.sha256(b"EMPTY_TABLE").hexdigest()

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
            }

        if validation_level.upper() == "ROW_COUNT":
            return {
                "status": "PASSED",
                "reason": "Row counts match",
                "source_count": source_count,
                "target_count": target_count,
                "mismatches": [],
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
            }

        return {
            "status": "PASSED",
            "reason": "Data hashes & Merkle root match",
            "source_count": source_count,
            "target_count": target_count,
            "source_merkle_root": source_merkle_root,
            "target_merkle_root": target_merkle_root,
            "mismatches": [],
        }
