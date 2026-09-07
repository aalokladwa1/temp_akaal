"""akaalEngine.intelligence.identity.fingerprint
=================================================
Deterministic fingerprinting for P7C.1 IntelligenceContext / IntelligenceArtifact
identity (P7C brief "Intelligence Artifact Identity" / "Context fingerprint").

Deliberately self-contained (no dependency on akaalPipeline.contracts.serialization):
akaalEngine must never depend on akaalPipeline (the dependency runs the other way --
akaalPipeline consumes akaalEngine authorities). This is the kernel's own fingerprint
space; it is not claimed to be interchangeable with AKAAL_CANONICAL_PROFILE_V1
fingerprints computed elsewhere in the repository.

Determinism contract, hostile-testable:
  * Identical inputs (same key/value pairs, any insertion order) -> identical hash.
  * Any single dimension change -> a different hash (no accidental collision from
    naive string concatenation -- each field is length-delimited before hashing).
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


def _assert_finite(obj: Any, path: str = "root") -> None:
    if obj is None or isinstance(obj, (bool, int, str)):
        return
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"Non-finite float at {path} cannot be fingerprinted")
        return
    if isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _assert_finite(item, f"{path}[{i}]")
        return
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"Non-string key {k!r} at {path} cannot be fingerprinted")
            _assert_finite(v, f"{path}.{k}")
        return
    raise TypeError(f"Non-JSON-safe type {type(obj).__name__} at {path} cannot be fingerprinted")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization: sorted keys, compact separators, no NaN/Inf."""
    _assert_finite(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_context_fingerprint(context: "Any") -> str:
    """Fingerprints an IntelligenceContext's identity-bearing dimensions. Any change
    to tenant, subject identity/version, canonical-state hash, or policy/algorithm
    version yields a different fingerprint -- this is the value compared against a
    persisted artifact's canonical_state_fingerprint to detect staleness."""
    payload = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    return sha256_hex(canonical_json(payload))


def compute_artifact_fingerprint(
    *,
    context_fingerprint: str,
    task: str,
    algorithm_version: str,
    policy_version: str,
    result_fingerprint: str,
    model_provider: str = "",
    model_id: str = "",
    model_version: str = "",
) -> str:
    """Fingerprints a generated artifact's full identity, binding it to the exact
    context it was generated against, the task/algorithm/policy versions used, the
    content produced, and (when applicable) the model/deployment/version identity
    (P7C brief "Model version pinning")."""
    payload = {
        "context_fingerprint": context_fingerprint,
        "task": task,
        "algorithm_version": algorithm_version,
        "policy_version": policy_version,
        "result_fingerprint": result_fingerprint,
        "model_provider": model_provider,
        "model_id": model_id,
        "model_version": model_version,
    }
    return sha256_hex(canonical_json(payload))
