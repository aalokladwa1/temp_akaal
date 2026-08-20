"""akaalPipeline.contracts.serialization
=====================================
Deterministic canonical JSON serialization & SHA-256 fingerprinting.
"""

import hashlib
import json
import types
from typing import Any, Mapping



def deep_freeze(obj: Any) -> Any:
    """Recursively converts dicts to MappingProxyType, lists to tuples, sets to frozensets."""
    if isinstance(obj, Mapping):
        return types.MappingProxyType({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(deep_freeze(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(deep_freeze(item) for item in obj)
    return obj


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert MappingProxyType and tuples to standard dicts/lists for json.dumps."""
    if isinstance(obj, (Mapping, types.MappingProxyType)):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_to_json_safe(v) for v in obj]
    return obj


def assert_json_safe(val: Any, path: str = "root") -> None:
    """Recursively assert value consists only of JSON primitives."""
    if val is None or isinstance(val, (bool, int, float, str)):
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


def canonical_serialize(obj: Any) -> str:
    """Serialize object to deterministic, key-sorted JSON string."""
    assert_json_safe(obj)
    safe_obj = _to_json_safe(obj)
    return json.dumps(safe_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)



def canonical_fingerprint(obj: Any) -> str:
    """Generate SHA-256 hex digest of deterministic canonical serialization."""
    serialized = canonical_serialize(obj)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
