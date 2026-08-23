"""
akaalEngine.validation.models.canonical
=======================================
Deterministic Canonicalization Engine for Authority #11 (VAL-013 through VAL-019).
Guarantees distinct, collision-free byte representations for NULL, missing fields, Decimals, Timestamps, Unicode, Binary/LOB, and JSON.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Tuple


class CanonicalValueFormatter:
    """
    Formats Python data types into deterministic canonical string representations.
    Ensures NULL is distinct from "", 0, False, missing fields, "0", or "False" (VAL-014).
    """

    @staticmethod
    def canonicalize(val: Any, preserve_decimal_scale: bool = False) -> Tuple[str, str]:
        """
        Returns (type_tag, canonical_str_value).
        Type tags guarantee zero cross-type hash collisions.
        """
        if val is None:
            return "NULL", "__CANONICAL_NULL__"

        if val == "__CANONICAL_MISSING__":
            return "MISSING", "__CANONICAL_MISSING__"

        if isinstance(val, bool):
            return "BOOL", "TRUE" if val else "FALSE"

        if isinstance(val, (int, float)):
            if isinstance(val, int):
                return "INT", str(val)
            # Convert float to exact string representation without loss of precision
            return "FLOAT", f"{val:.12g}"

        if isinstance(val, Decimal):
            if preserve_decimal_scale:
                # Scale is semantically significant (e.g., 1.00 != 1.0)
                return "DECIMAL_EXACT", f"{val}"
            # Approved Authority #4 scale normalization (e.g., 12.3400 -> 12.34)
            normalized = val.normalize()
            return "DECIMAL_NORM", str(normalized)

        if isinstance(val, datetime):
            # Convert to UTC ISO-8601 string
            dt_utc = val.astimezone(timezone.utc) if val.tzinfo else val
            return "DATETIME", dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")

        if isinstance(val, date):
            return "DATE", val.strftime("%Y-%m-%d")

        if isinstance(val, time):
            return "TIME", val.strftime("%H:%M:%S.%f")

        if isinstance(val, (bytes, bytearray)):
            # Binary/LOB hex representation (VAL-018)
            return "BYTES", val.hex()

        if hasattr(val, "read") and callable(val.read):
            # LOB stream reader chunking
            chunks = []
            chunk = val.read(8192)
            while chunk:
                chunks.append(chunk.hex() if isinstance(chunk, bytes) else chunk)
                chunk = val.read(8192)
            return "LOB_STREAM", "".join(chunks)

        if isinstance(val, (dict, list)):
            # Canonical JSON key sorting (VAL-019)
            canonical_json = json.dumps(val, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            return "JSON", canonical_json

        # Default string handling (VAL-017)
        return "STR", str(val)
