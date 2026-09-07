"""akaalEngine.intelligence.knowledge.constraint_projection
=============================================================
Trusted canonical constraint projection for P7C.8 (P7C brief permanent law:
"CANONICAL AKAAL TRUTH OUTRANKS CALLER-SUPPLIED CONTEXT" / "P7C optimizes
within the legal envelope, never around it").

This module is NOT a second residency, security, or capability authority. It
is a pure, read-only PROJECTION: for each candidate region/capability, it asks
the REAL, already-canonical, injected authorization decision-maker (in
production: `akaalPipeline.security.central_authorization.
CentralAuthorizationEngine`, the same engine every other protected P7C
operation already delegates to -- see akaalEngine.intelligence.mediation) "is
this tenant permitted to use this region/capability", and only reports back
what that engine actually decided. It stores no policy of its own and makes no
decision of its own.

Trust semantics enforced here (hostile-tested):
  FINAL_FEASIBLE_SET = CANONICAL_FEASIBLE_SET ∩ CALLER_REQUESTED_SET
never a union, never a caller-side override. A caller can only ever narrow
what the canonical projection already allows -- supplying a region the
canonical authority denies can never add it back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, FrozenSet, Mapping, Optional

from akaalEngine.intelligence.identity.fingerprint import canonical_json, sha256_hex

# Callable[[tenant_id, region], bool] -- in production this closes over the
# real CentralAuthorizationEngine.authorize(); in tests it can be any real
# decision function. Never a caller-supplied boolean.
RegionAuthorizer = Callable[[str, str], bool]
# Callable[[tenant_id, region, capability], bool] -- same discipline.
CapabilityAuthorizer = Callable[[str, str, str], bool]


@dataclass(frozen=True)
class TrustedStrategyConstraintSnapshot:
    """The canonical feasible set, as decided by the real authorization
    authority -- never as asserted by a caller. `source_fingerprint` binds this
    snapshot to the exact canonical decisions it was built from, so a later
    caller can detect (via P7C.1 staleness) if canonical policy has since
    changed underneath a cached snapshot."""

    tenant_id: str
    allowed_regions: FrozenSet[str]
    region_capability_map: Mapping[str, FrozenSet[str]]
    source_fingerprint: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "allowed_regions": sorted(self.allowed_regions),
            "region_capability_map": {k: sorted(v) for k, v in self.region_capability_map.items()},
            "source_fingerprint": self.source_fingerprint,
            "generated_at": self.generated_at,
        }


def project_trusted_constraints(
    tenant_id: str,
    *,
    candidate_regions: FrozenSet[str],
    region_authorizer: RegionAuthorizer,
    capability_universe: Optional[FrozenSet[str]] = None,
    capability_authorizer: Optional[CapabilityAuthorizer] = None,
) -> TrustedStrategyConstraintSnapshot:
    """Builds the canonical feasible set by asking the real authorizer about
    every candidate region individually -- there is no bulk/implicit grant.
    `region_authorizer`/`capability_authorizer` are the only sources of truth;
    this function performs zero policy reasoning of its own."""
    allowed_regions = frozenset(r for r in candidate_regions if region_authorizer(tenant_id, r))

    region_capability_map: Mapping[str, FrozenSet[str]] = {}
    if capability_universe is not None and capability_authorizer is not None:
        region_capability_map = {
            region: frozenset(cap for cap in capability_universe if capability_authorizer(tenant_id, region, cap))
            for region in allowed_regions
        }

    fingerprint_payload = {
        "tenant_id": tenant_id,
        "allowed_regions": sorted(allowed_regions),
        "region_capability_map": {k: sorted(v) for k, v in region_capability_map.items()},
    }
    source_fingerprint = sha256_hex(canonical_json(fingerprint_payload))

    return TrustedStrategyConstraintSnapshot(
        tenant_id=tenant_id,
        allowed_regions=allowed_regions,
        region_capability_map=region_capability_map,
        source_fingerprint=source_fingerprint,
    )


def narrow_by_caller_preference(
    canonical_regions: FrozenSet[str], caller_requested_regions: Optional[FrozenSet[str]]
) -> FrozenSet[str]:
    """The ONLY legal way caller input may affect the feasible region set:
    intersection, never union. If the caller requests nothing, the full
    canonical set stands. If the caller requests regions the canonical
    authority never granted, those regions simply cannot appear -- there is no
    code path here that adds anything to `canonical_regions`."""
    if caller_requested_regions is None:
        return canonical_regions
    return canonical_regions & caller_requested_regions
