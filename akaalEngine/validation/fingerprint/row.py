"""
akaalEngine.validation.fingerprint.row
======================================
DeterministicRowFingerprinter for Authority #11 (VAL-021).
Creates framed, collision-free SHA-256 fingerprints over schema identity and canonical column values.
Disambiguates NULL values from missing document fields.
"""

import hashlib
from typing import Any, Dict, List, Optional

from akaalEngine.validation.models.canonical import CanonicalValueFormatter


class DeterministicRowFingerprinter:
    """
    Computes a framed, deterministic SHA-256 fingerprint for a single data row.
    Framing format:
      COL_NAME|TYPE_TAG|BYTE_LEN|CANONICAL_BYTES;...
    Disambiguates missing fields ({"x": None} vs {}) and distinct data types.
    """

    @staticmethod
    def compute_fingerprint(
        row: Dict[str, Any],
        column_names: Optional[List[str]] = None,
        preserve_decimal_scale: bool = False,
    ) -> str:
        cols = column_names or sorted(row.keys())
        hasher = hashlib.sha256()

        for col in cols:
            if col not in row:
                # Disambiguate missing document field from NULL value
                type_tag, canon_str = CanonicalValueFormatter.canonicalize("__CANONICAL_MISSING__")
            else:
                val = row[col]
                type_tag, canon_str = CanonicalValueFormatter.canonicalize(val, preserve_decimal_scale=preserve_decimal_scale)

            val_bytes = canon_str.encode("utf-8")
            col_bytes = col.encode("utf-8")
            type_bytes = type_tag.encode("utf-8")

            # Explicit length framing
            frame = (
                f"{len(col_bytes)}:".encode("utf-8")
                + col_bytes
                + f":{type_bytes.decode('utf-8')}:{len(val_bytes)}:".encode("utf-8")
                + val_bytes
                + b";"
            )
            hasher.update(frame)

        return hasher.hexdigest()
