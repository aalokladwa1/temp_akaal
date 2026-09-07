"""
akaalEngine.fabric.multi_cloud.models
========================================
P7B.27 -- Multi-Cloud Operation data model.

A site's cloud identity is ALWAYS derived from its Environment record (P7B.1) -- never
inferred from site_id/region strings, and never a second, parallel identity
representation. `CloudIdentity.native_boundary_key` is exactly
`Environment.boundary.native_key()` -- the same value akaalEngine.fabric.environment
already uses to prevent one cloud account/subscription/project/tenancy from colliding
with another, reused here rather than re-derived.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class CloudOperationalState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CloudIdentity:
    environment_type: str
    native_boundary_key: Tuple[str, ...] = field(default_factory=tuple)

    def as_key(self) -> Tuple[str, Tuple[str, ...]]:
        """Hashable composite key -- environment_type ALONE is never sufficient (two
        different AWS accounts are two different clouds for this module's purposes, not
        one 'AWS' bucket)."""
        return (self.environment_type, self.native_boundary_key)


@dataclass(frozen=True)
class CloudHealthSnapshot:
    cloud_identity: CloudIdentity
    site_ids: Tuple[str, ...] = field(default_factory=tuple)
    available_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    degraded_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    unavailable_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    state: CloudOperationalState = CloudOperationalState.UNKNOWN
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    def is_operationally_usable(self) -> bool:
        return self.state in (CloudOperationalState.HEALTHY, CloudOperationalState.DEGRADED)
