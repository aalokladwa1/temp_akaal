"""
akaalIPC.protocol.versions
============================
Explicit protocol compatibility semantics.

Protocol negotiation happens exactly once, before a request is allowed to
reach schema validation or the downstream application boundary. Nothing
else in akaalIPC should re-implement version comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional

from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error

# The protocol version this build of akaalIPC speaks natively.
CURRENT_PROTOCOL_VERSION = "1.0.0"

# The full set of protocol versions this build will accept from a caller.
# A caller on an unsupported version is rejected — never silently coerced.
SUPPORTED_PROTOCOL_VERSIONS: FrozenSet[str] = frozenset({"1.0.0"})


@dataclass(frozen=True)
class CompatibilityResult:
    is_compatible: bool
    requested_version: str
    negotiated_version: Optional[str] = None
    error: Optional[IPCError] = None


def check_protocol_compatibility(
    requested_version: str,
    *,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> CompatibilityResult:
    if not requested_version or not isinstance(requested_version, str):
        return CompatibilityResult(
            is_compatible=False,
            requested_version=str(requested_version),
            error=make_error(
                IPCErrorCategory.PROTOCOL_INCOMPATIBLE,
                code="PROTOCOL_VERSION_MISSING",
                message="Request did not declare a protocol_version.",
                correlation_id=correlation_id,
                request_id=request_id,
            ),
        )

    if requested_version not in SUPPORTED_PROTOCOL_VERSIONS:
        return CompatibilityResult(
            is_compatible=False,
            requested_version=requested_version,
            error=make_error(
                IPCErrorCategory.PROTOCOL_INCOMPATIBLE,
                code="PROTOCOL_VERSION_UNSUPPORTED",
                message=(
                    f"Protocol version '{requested_version}' is not supported. "
                    f"Supported versions: {sorted(SUPPORTED_PROTOCOL_VERSIONS)}."
                ),
                correlation_id=correlation_id,
                request_id=request_id,
                details={"supported_versions": sorted(SUPPORTED_PROTOCOL_VERSIONS)},
            ),
        )

    return CompatibilityResult(
        is_compatible=True,
        requested_version=requested_version,
        negotiated_version=requested_version,
    )
