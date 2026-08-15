"""
AKAAL Canonical Data Checksum Authority
========================================
Implements deterministic, typed, length-prefixed canonical row hashing
for physical data integrity verification across all database adapters.
"""

import hashlib
from decimal import Decimal
from datetime import date, time, datetime
from typing import List, Dict, Any, Sequence, Tuple, Union


def canonical_hash_row(row_dict: Dict[str, Any]) -> str:
    """
    Computes a deterministic, typed, length-prefixed SHA-256 hash for a single row dict.
    Columns are sorted alphabetically.
    Types and nullability are unambiguously encoded:
    - N: None / NULL
    - S: string
    - I: integer / int
    - F: float / decimal
    - B: boolean
    - D: date / time / datetime
    - X: bytes / binary
    """
    parts = []
    for col in sorted(row_dict.keys()):
        val = row_dict[col]
        col_bytes = str(col).encode('utf-8')
        col_hdr = f"{len(col_bytes)}:{col}:".encode('utf-8')

        if val is None:
            val_hdr = b"N:0:"
            val_bytes = b""
        elif isinstance(val, bool):
            val_bytes = (b"true" if val else b"false")
            val_hdr = f"B:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (int, float, Decimal)):
            if isinstance(val, float):
                val_str = f"{val:.8f}".rstrip('0').rstrip('.')
            else:
                val_str = str(val)
            val_bytes = val_str.encode('utf-8')
            tag = "I" if isinstance(val, int) and not isinstance(val, bool) else "F"
            val_hdr = f"{tag}:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (datetime, date, time)):
            val_bytes = val.isoformat().encode('utf-8')
            val_hdr = f"D:{len(val_bytes)}:".encode('utf-8')
        elif isinstance(val, (bytes, bytearray, memoryview)):
            val_bytes = bytes(val).hex().encode('utf-8')
            val_hdr = f"X:{len(val_bytes)}:".encode('utf-8')
        else:
            val_bytes = str(val).encode('utf-8')
            val_hdr = f"S:{len(val_bytes)}:".encode('utf-8')

        parts.append(col_hdr + val_hdr + val_bytes)

    row_canonical_bytes = b"|".join(parts)
    return hashlib.sha256(row_canonical_bytes).hexdigest()


def compute_canonical_table_checksum(rows: List[Dict[str, Any]]) -> str:
    """
    Computes a cumulative SHA-256 digest over an ordered list of row dicts.
    If rows is empty, returns digest of b"EMPTY_TABLE".
    """
    if not rows:
        return hashlib.sha256(b"EMPTY_TABLE").hexdigest()

    table_digest = hashlib.sha256()
    for row in rows:
        row_hash = canonical_hash_row(row)
        table_digest.update(row_hash.encode('utf-8'))

    return table_digest.hexdigest()
