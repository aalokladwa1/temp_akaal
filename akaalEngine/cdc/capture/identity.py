"""
akaalEngine.cdc.capture.identity
================================
Type-safe Primary Key identity encoder, decoder, and maker for CDC source adapters.
Guarantees that primary key identity and types (int, str, float, composite tuples, etc.)
survive JSON snapshot serialization and deserialization without manufacturing false CDC events.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("akaalEngine.cdc.capture.identity")


def encode_pk_val(val: Any) -> Tuple[str, Any]:
    """Tag a single PK column value with explicit type information."""
    if val is None:
        return ("none", None)
    elif isinstance(val, bool):
        return ("bool", val)
    elif isinstance(val, int):
        return ("int", val)
    elif isinstance(val, float):
        return ("float", val)
    elif isinstance(val, str):
        return ("str", val)
    elif isinstance(val, bytes):
        return ("bytes", val.hex())
    else:
        return ("str", str(val))


def decode_pk_val(tagged: Any) -> Any:
    """Decode a tagged PK column value back to its native Python type."""
    if not isinstance(tagged, (list, tuple)) or len(tagged) != 2:
        raise ValueError(f"Invalid tagged PK value structure: {tagged}")
    tag, val = tagged
    if tag == "none":
        return None
    elif tag == "bool":
        return bool(val)
    elif tag == "int":
        return int(val)
    elif tag == "float":
        return float(val)
    elif tag == "str":
        return str(val)
    elif tag == "bytes":
        return bytes.fromhex(val) if isinstance(val, str) else bytes(val)
    else:
        return str(val)


def encode_pk_key(key: Any) -> str:
    """
    Encode an in-memory PK key (int, str, float, or tuple) into a canonical,
    type-preserving JSON key string.
    """
    if isinstance(key, tuple):
        tagged = ["composite", [encode_pk_val(x) for x in key]]
    else:
        tagged = ["single", encode_pk_val(key)]
    return json.dumps(tagged, separators=(',', ':'))


def decode_pk_key(key_str: str) -> Any:
    """
    Decode a type-preserving JSON key string back into its native in-memory PK key.
    Raises ValueError for legacy untagged string keys to prevent ambiguous/false delta events.
    """
    try:
        data = json.loads(key_str)
        if isinstance(data, list) and len(data) == 2:
            kind, payload = data
            if kind == "single":
                return decode_pk_val(payload)
            elif kind == "composite" and isinstance(payload, list):
                return tuple(decode_pk_val(x) for x in payload)
    except Exception:
        pass
    raise ValueError(f"Legacy or untagged PK key string cannot be safely decoded: {key_str}")


def make_pk_key(row_dict: Dict[str, Any], pk_cols: Sequence[str]) -> Any:
    """
    Extract native primary key values from a database row dictionary.
    Preserves exact Python types (int vs str vs tuple).
    """
    if not pk_cols:
        if isinstance(row_dict, dict):
            vals = [row_dict[k] for k in sorted(row_dict.keys())]
            return tuple(vals) if len(vals) > 1 else (vals[0] if vals else "")
        return str(row_dict).strip()

    vals = []
    for c in pk_cols:
        val = row_dict.get(c, row_dict.get(c.lower(), row_dict.get(c.upper())))
        vals.append(val)
    return tuple(vals) if len(vals) > 1 else (vals[0] if vals else "")
