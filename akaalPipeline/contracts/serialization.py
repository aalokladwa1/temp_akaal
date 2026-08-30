"""akaalPipeline.contracts.serialization
=====================================
Deterministic canonical JSON serialization & SHA-256 fingerprinting.
Implements AKAAL_CANONICAL_PROFILE_V1:
- JSON-safety validation (finite numbers only, non-string keys rejected)
- Recursive Unicode NFC normalization
- Deterministic canonical JSON serialization (UTF-16 code unit key sorting, compact delimiters)
- UTF-8 byte encoding & SHA-256 fingerprinting
Note: This profile is AKAAL-specific and is not claimed to be RFC 8785/JCS wire-compatible.
"""

from __future__ import annotations

import hashlib
import json
import math
import types
import unicodedata
from typing import Any, Mapping

AKAAL_CANONICAL_PROFILE_V1 = "AKAAL_CANONICAL_PROFILE_V1"


def deep_freeze(obj: Any) -> Any:
    """Recursively converts dicts to MappingProxyType, lists to tuples, sets to frozensets."""
    if isinstance(obj, Mapping):
        return types.MappingProxyType({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(deep_freeze(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(deep_freeze(item) for item in obj)
    return obj


def normalize_nfc(val: Any) -> Any:
    """Recursively apply Unicode NFC normalization to all string elements and dictionary keys."""
    if isinstance(val, str):
        return unicodedata.normalize("NFC", val)
    if isinstance(val, (dict, Mapping, types.MappingProxyType)):
        return {unicodedata.normalize("NFC", str(k)): normalize_nfc(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [normalize_nfc(item) for item in val]
    if isinstance(val, (set, frozenset)):
        return [normalize_nfc(item) for item in sorted(val, key=lambda x: unicodedata.normalize("NFC", str(x)))]
    return val


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert MappingProxyType and tuples to standard dicts/lists for json.dumps."""
    if isinstance(obj, (Mapping, types.MappingProxyType)):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_to_json_safe(v) for v in obj]
    return obj


def assert_json_safe(val: Any, path: str = "root") -> None:
    """Recursively assert value consists only of JSON primitives and finite numbers."""
    if val is None or isinstance(val, (bool, int, str)):
        return
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Non-finite float {val!r} is not valid JSON at {path} per AKAAL_CANONICAL_PROFILE_V1")
        return
    if isinstance(val, (list, tuple, set, frozenset)):
        for idx, item in enumerate(val):
            assert_json_safe(item, f"{path}[{idx}]")
        return
    if isinstance(val, (dict, Mapping, types.MappingProxyType)):
        for k, v in val.items():
            if not isinstance(k, str):
                raise TypeError(f"Non-string JSON key {k!r} at {path}")
            assert_json_safe(v, f"{path}.{k}")
        return
    raise TypeError(f"Non-JSON-safe type {type(val).__name__} at {path}")


def _jcs_key_sort(key: str) -> bytes:
    """Sort keys by UTF-16 code units (historical identifier; part of AKAAL_CANONICAL_PROFILE_V1)."""
    return key.encode("utf-16-be")


def _canonical_jcs(obj: Any) -> str:
    """Deterministic AKAAL canonical JSON serializer (historical identifier; part of AKAAL_CANONICAL_PROFILE_V1)."""
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        if obj.is_integer():
            return f"{int(obj)}"
        return json.dumps(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, (list, tuple)):
        items = [_canonical_jcs(item) for item in obj]
        return "[" + ",".join(items) + "]"
    if isinstance(obj, (dict, Mapping, types.MappingProxyType)):
        sorted_keys = sorted(obj.keys(), key=_jcs_key_sort)
        pairs = [f"{json.dumps(k, ensure_ascii=False)}:{_canonical_jcs(obj[k])}" for k in sorted_keys]
        return "{" + ",".join(pairs) + "}"
    raise TypeError(f"Non-JSON-safe type {type(obj).__name__}")


def canonical_serialize(obj: Any) -> str:
    """Serialize object to deterministic AKAAL canonical JSON string per AKAAL_CANONICAL_PROFILE_V1."""
    assert_json_safe(obj)
    nfc_obj = normalize_nfc(obj)
    return _canonical_jcs(nfc_obj)



def canonical_serialize_bytes(obj: Any) -> bytes:
    """Serialize object to deterministic UTF-8 bytes per AKAAL_CANONICAL_PROFILE_V1."""
    return canonical_serialize(obj).encode("utf-8")


def canonical_fingerprint(obj: Any) -> str:
    """Generate SHA-256 hex digest of deterministic canonical serialization."""
    serialized = canonical_serialize_bytes(obj)
    return hashlib.sha256(serialized).hexdigest()
