"""
akaalEngine.extensions.supply_chain.canonical
================================================
Deterministic canonical serialization of the security-relevant fields of an
ExtensionManifest, bound together with the artifact digest into one signed envelope.

Why this exists: signing only the raw artifact digest lets an attacker keep a validly
signed artifact but relabel its metadata (extension_id, version, publisher_id, requested
permissions, capability declarations, provider/strategy identities) since none of that
would invalidate a digest-only signature. This module builds the exact byte sequence a
publisher must sign, and PackageIntegrityValidator verifies the provenance signature
against these bytes -- so mutating ANY field bound here invalidates the signature.

Determinism requirements: all collections are sorted before serialization; no field
relies on Python's dict/set iteration order; no floats; every value that participates is
a plain string/int/bool, never a live object.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from akaalEngine.extensions.models.extension import ExtensionManifest


def _capability_to_dict(cap) -> Dict[str, Any]:
    return {
        "capability_name": cap.capability_name,
        "is_supported": cap.is_supported,
        "declared_proof_level": cap.declared_proof_level.value,
        "required_dependencies": sorted(cap.required_dependencies),
        "restrictions": sorted(cap.restrictions),
    }


def _strategy_to_dict(strat) -> Dict[str, Any]:
    return {
        "strategy_id": strat.strategy_id.value,
        "authority_id": strat.authority_id.value,
        "provider_id": strat.provider_id.value,
        "contract_version_range": strat.contract_version_range.raw_expression,
        "implementation_version": strat.implementation_version,
        "capabilities": sorted(
            (_capability_to_dict(c) for c in strat.capabilities),
            key=lambda d: d["capability_name"],
        ),
    }


def _provider_to_dict(prov) -> Dict[str, Any]:
    return {
        "provider_id": prov.provider_id.value,
        "vendor_name": prov.vendor_name,
        "display_name": prov.display_name,
        "family": prov.family,
        "version": prov.version,
        "strategies": sorted(
            (_strategy_to_dict(s) for s in prov.strategies),
            key=lambda d: d["strategy_id"],
        ),
    }


def _permission_request_to_dict(perm) -> Dict[str, Any]:
    if perm is None:
        return {}
    return {
        "filesystem_read_paths": sorted(perm.filesystem_read_paths),
        "filesystem_write_paths": sorted(perm.filesystem_write_paths),
        "network_egress_hosts": sorted(perm.network_egress_hosts),
        "environment_variables": sorted(perm.environment_variables),
        "secret_references": sorted(perm.secret_references),
        "host_functions": sorted(perm.host_functions),
        "cpu_time_budget_seconds": perm.cpu_time_budget_seconds,
        "memory_budget_bytes": perm.memory_budget_bytes,
        "wall_clock_budget_seconds": perm.wall_clock_budget_seconds,
    }


def build_canonical_envelope(manifest: ExtensionManifest, artifact_digest_hex: str) -> Dict[str, Any]:
    """
    Builds the plain-dict canonical representation of everything a package signature
    must bind. Exposed separately from the byte-serialization step for testability.
    """
    return {
        "schema": "akaal.extension.signed_envelope.v1",
        "artifact_digest_hex": artifact_digest_hex.lower(),
        "extension_id": manifest.extension_id.value,
        "version": manifest.version,
        "publisher_id": manifest.publisher_id or "",
        "origin": manifest.origin.value,
        "isolation_mode": manifest.isolation_mode.value,
        "engine_version_range": manifest.engine_version_range.raw_expression,
        "permission_request": _permission_request_to_dict(manifest.permission_request),
        "provider_contributions": sorted(
            (_provider_to_dict(p) for p in manifest.provider_contributions),
            key=lambda d: d["provider_id"],
        ),
    }


def canonical_envelope_bytes(manifest: ExtensionManifest, artifact_digest_hex: str) -> bytes:
    """
    Deterministic UTF-8 JSON bytes for the canonical envelope: sorted keys, no whitespace
    ambiguity, fixed separators -- the same manifest+digest always produces byte-identical
    output, which is required for signature verification to be meaningful.
    """
    envelope = build_canonical_envelope(manifest, artifact_digest_hex)
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_envelope_digest(manifest: ExtensionManifest, artifact_digest_hex: str) -> bytes:
    """SHA-256 digest of the canonical envelope bytes -- this is what gets signed/verified."""
    return hashlib.sha256(canonical_envelope_bytes(manifest, artifact_digest_hex)).digest()
