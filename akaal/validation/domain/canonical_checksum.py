"""
AKAAL Canonical Data Checksum Authority
========================================
Implements deterministic, typed, length-prefixed canonical row & table hashing
for physical data integrity verification across all database adapters.

Domain Invariants:
- Typed & length-prefixed column encoding (prevents boundary collisions)
- Column identity normalized to lowercase unquoted names
- Float & Decimal canonical normalization via Decimal.normalize()
- Datetime timezone normalization to UTC ISO 8601
- Unicode string canonicalization via unicodedata.normalize('NFC')
- Explicit domain separation between empty tables and physical row datasets
- Memory-bounded streaming iterable processing for enterprise datasets
- Deterministic order-independent fallback for tables lacking primary keys
"""

import hashlib
import unicodedata
from decimal import Decimal
from datetime import date, time, datetime, timezone
from typing import Dict, Any, Iterable, List, Optional


def canonical_hash_row(row_dict: Dict[str, Any]) -> str:
    """
    Computes a deterministic, typed, length-prefixed SHA-256 hash for a single row dict.
    Columns are sorted alphabetically by normalized lowercase name.
    Types and nullability are unambiguously encoded:
    - N: None / NULL
    - B: boolean (true/false)
    - I: integer / int
    - F: float / decimal (normalized)
    - D: date / time / datetime (UTC ISO 8601)
    - X: bytes / binary (hex string)
    - S: string (Unicode NFC normalized)
    """
    parts = []
    # Sort by normalized column identity
    sorted_cols = sorted(row_dict.keys(), key=lambda c: str(c).strip('"`[]').lower())
    
    for col in sorted_cols:
        col_clean = str(col).strip('"`[]').lower()
        val = row_dict[col]
        col_bytes = col_clean.encode('utf-8')
        col_hdr = f"{len(col_bytes)}:{col_clean}:".encode('utf-8')

        if val is None:
            val_hdr = b"N:0:"
            val_bytes = b""
        elif isinstance(val, bool):
            val_bytes = b"true" if val else b"false"
            val_hdr = f"B:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (int, float, Decimal)):
            if isinstance(val, int) and not isinstance(val, bool):
                val_bytes = str(val).encode('utf-8')
                val_hdr = f"I:{len(val_bytes)}:".encode('utf-8')
            else:
                try:
                    d_val = Decimal(str(val)) if isinstance(val, float) else val
                    d_norm = d_val.normalize()
                    # Format standard notation without trailing exponent artifact for integral decimals
                    val_str = format(d_norm, 'f') if d_norm == d_norm.to_integral_value() else str(d_norm)
                except Exception:
                    val_str = str(val)
                val_bytes = val_str.encode('utf-8')
                val_hdr = f"F:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (datetime, date, time)):
            if isinstance(val, datetime):
                if val.tzinfo is not None:
                    val_utc = val.astimezone(timezone.utc)
                    val_str = val_utc.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
                else:
                    val_str = val.strftime('%Y-%m-%dT%H:%M:%S.%f')
            else:
                val_str = val.isoformat()
            val_bytes = val_str.encode('utf-8')
            val_hdr = f"D:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (bytes, bytearray, memoryview)):
            val_bytes = bytes(val).hex().encode('utf-8')
            val_hdr = f"X:{len(val_bytes)}:".encode('utf-8')
        else:
            val_norm = unicodedata.normalize('NFC', str(val))
            val_bytes = val_norm.encode('utf-8')
            val_hdr = f"S:{len(val_bytes)}:".encode('utf-8')

        parts.append(col_hdr + val_hdr + val_bytes)

    row_canonical_bytes = b"|".join(parts)
    return hashlib.sha256(row_canonical_bytes).hexdigest()


def compute_canonical_table_checksum(
    rows: Iterable[Dict[str, Any]],
    order_independent: bool = False
) -> str:
    """
    Computes a cumulative SHA-256 digest over an iterable of row dicts.
    Uses strict domain separation to ensure empty table state cannot collide
    with any physical row dataset.

    Memory bounded: supports generators/streaming fetchers without full list materialization.
    If order_independent is True (tables without PK), row hashes are sorted deterministically.
    """
    if order_independent:
        # Sort row hashes in memory for tables lacking a deterministic PK column
        row_hashes = [canonical_hash_row(r) for r in rows]
        if not row_hashes:
            return hashlib.sha256(b"AKAAL_CANONICAL_CHECKSUM_V1:DOMAIN_EMPTY_TABLE").hexdigest()
        table_digest = hashlib.sha256(b"AKAAL_CANONICAL_CHECKSUM_V1:DOMAIN_ROW_DATA\n")
        for rh in sorted(row_hashes):
            table_digest.update(rh.encode('utf-8'))
        return table_digest.hexdigest()

    table_digest = hashlib.sha256(b"AKAAL_CANONICAL_CHECKSUM_V1:DOMAIN_ROW_DATA\n")
    count = 0
    for row in rows:
        row_hash = canonical_hash_row(row)
        table_digest.update(row_hash.encode('utf-8'))
        count += 1

    if count == 0:
        return hashlib.sha256(b"AKAAL_CANONICAL_CHECKSUM_V1:DOMAIN_EMPTY_TABLE").hexdigest()

    return table_digest.hexdigest()
