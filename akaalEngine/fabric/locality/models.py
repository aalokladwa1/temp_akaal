"""
akaalEngine.fabric.locality.models
=====================================
P7B.12 -- Data Locality Model.

Canonical representation of where migration-relevant data and execution resources
actually reside, across the dimensions the Group-2 directive names: cloud/provider,
country, jurisdiction, sovereignty zone, region, availability zone, datacenter, network,
Kubernetes cluster, execution site, storage location.

ABSOLUTE LAW, enforced structurally (never as documentation only):

    UNKNOWN MUST REMAIN UNKNOWN.

  * A dimension with no explicitly-supplied value is `None`, never inferred from another
    field. There is no helper anywhere in this module that derives country from region,
    jurisdiction from cloud provider, or residency from reachability -- callers who want
    that must prove it themselves and construct a record with the actual proven value.
  * A `LocalityRecord.confidence` of CLAIMED is NEVER treated as equivalent to PROVEN.
    `LocalityRecord.proven_value_for()` returns `None` for any dimension whose value is
    known only at CLAIMED confidence, even though `value_for()` (unchecked) would return
    the same string -- this distinction is exactly what stops "caller-forged locality"
    (the P7B Group-2 locality hostile matrix) from satisfying a policy that requires
    proof.
  * A stale record is never treated as current -- `proven_value_for()` returns `None` for
    a stale record regardless of confidence.

This module has no policy-enforcement logic (that is P7B.15's job, layered above this
model) -- it only ever answers "what do we know, and how confidently", never "is this
allowed". `satisfies()` below is a narrow three-valued helper (True / False / None-for-
unknown) that a policy layer composes with actual authorization/residency rules; it is
not itself a residency decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Set


class LocalityDimension(str, Enum):
    CLOUD_PROVIDER = "CLOUD_PROVIDER"
    COUNTRY = "COUNTRY"
    JURISDICTION = "JURISDICTION"
    SOVEREIGNTY_ZONE = "SOVEREIGNTY_ZONE"
    REGION = "REGION"
    AVAILABILITY_ZONE = "AVAILABILITY_ZONE"
    DATACENTER = "DATACENTER"
    NETWORK = "NETWORK"
    KUBERNETES_CLUSTER = "KUBERNETES_CLUSTER"
    EXECUTION_SITE = "EXECUTION_SITE"
    STORAGE_LOCATION = "STORAGE_LOCATION"


class LocalityConfidence(str, Enum):
    """Strictly ordered. CLAIMED is never treated as equivalent to PROVEN -- see module
    docstring. There is deliberately no numeric rank helper exposed here beyond the
    ordering already implied by `proven_value_for` refusing anything below PROVEN, to
    avoid tempting callers into ad-hoc numeric comparisons that could silently drift from
    this rule."""
    UNKNOWN = "UNKNOWN"
    CLAIMED = "CLAIMED"
    PROVEN = "PROVEN"


class LocalitySubjectRole(str, Enum):
    """What role the located subject plays in a migration's data path -- required so a
    residency evaluation (P7B.15) can walk the whole movement path (source -> network ->
    relay -> staging -> execution site -> target -> validation/evidence destination)
    rather than only checking two endpoints."""
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    STAGING = "STAGING"
    RELAY = "RELAY"
    EXECUTION_SITE = "EXECUTION_SITE"
    NETWORK_HOP = "NETWORK_HOP"
    VALIDATION_EVIDENCE_DESTINATION = "VALIDATION_EVIDENCE_DESTINATION"


class LocalityValidationError(ValueError):
    pass


@dataclass(frozen=True)
class LocalityRecord:
    """
    Immutable record of what is known about where one subject (an opaque `subject_ref`
    into a canonical fabric record -- Environment, ExecutionSite, CloudResourceLocator,
    ConnectivityEdge, etc.) resides, for one role in one migration's data path, scoped to
    one tenant. A subject can have multiple LocalityRecords over time (re-observation) and
    the same physical thing can appear under multiple roles across different migrations
    (e.g. an execution site as EXECUTION_SITE in one migration, RELAY in another) -- this
    module intentionally does not collapse those into one record.
    """
    subject_ref: str
    subject_role: LocalitySubjectRole
    tenant_id: str
    cloud_provider: Optional[str] = None
    country: Optional[str] = None
    jurisdiction: Optional[str] = None
    sovereignty_zone: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    datacenter: Optional[str] = None
    network: Optional[str] = None
    kubernetes_cluster: Optional[str] = None
    execution_site: Optional[str] = None
    storage_location: Optional[str] = None
    confidence: LocalityConfidence = LocalityConfidence.UNKNOWN
    provenance_source: str = "UNKNOWN"
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stale: bool = False

    _DIMENSION_ATTR = {
        LocalityDimension.CLOUD_PROVIDER: "cloud_provider",
        LocalityDimension.COUNTRY: "country",
        LocalityDimension.JURISDICTION: "jurisdiction",
        LocalityDimension.SOVEREIGNTY_ZONE: "sovereignty_zone",
        LocalityDimension.REGION: "region",
        LocalityDimension.AVAILABILITY_ZONE: "availability_zone",
        LocalityDimension.DATACENTER: "datacenter",
        LocalityDimension.NETWORK: "network",
        LocalityDimension.KUBERNETES_CLUSTER: "kubernetes_cluster",
        LocalityDimension.EXECUTION_SITE: "execution_site",
        LocalityDimension.STORAGE_LOCATION: "storage_location",
    }

    def __post_init__(self) -> None:
        if not self.subject_ref or not self.subject_ref.strip():
            raise LocalityValidationError("LocalityRecord.subject_ref must be non-empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise LocalityValidationError("LocalityRecord.tenant_id must be non-empty.")
        if not self.provenance_source or not self.provenance_source.strip():
            raise LocalityValidationError(
                "LocalityRecord.provenance_source must be non-empty -- unknown provenance "
                "must be explicitly declared as 'UNKNOWN', never omitted."
            )
        # Confidence PROVEN with zero dimensions populated is almost certainly a caller
        # bug (nothing was actually proven) -- fail loudly rather than accept silently.
        if self.confidence == LocalityConfidence.PROVEN and not self._any_dimension_set():
            raise LocalityValidationError(
                "LocalityRecord declares confidence=PROVEN but no locality dimension is "
                "populated; a PROVEN record must actually prove something."
            )

    def _any_dimension_set(self) -> bool:
        return any(getattr(self, attr) is not None for attr in self._DIMENSION_ATTR.values())

    def value_for(self, dimension: LocalityDimension) -> Optional[str]:
        """Raw value regardless of confidence -- callers that need PROOF must use
        `proven_value_for` instead. Exposed separately so a UI/audit trail can honestly
        display an unproven CLAIMED value as a claim, without a policy engine
        accidentally treating it as fact."""
        return getattr(self, self._DIMENSION_ATTR[dimension])

    def proven_value_for(self, dimension: LocalityDimension) -> Optional[str]:
        """Returns the value ONLY if this record is fresh (not stale) and at PROVEN
        confidence; otherwise None. This is the ONLY accessor a residency/policy
        evaluation (P7B.15) may use to decide something is truthfully known -- using
        `value_for` for a policy decision is exactly the "locality claim != proven
        locality" bug class this method exists to prevent."""
        if self.stale or self.confidence != LocalityConfidence.PROVEN:
            return None
        return self.value_for(dimension)

    def is_proven(self, dimension: LocalityDimension) -> bool:
        return self.proven_value_for(dimension) is not None

    def satisfies(self, dimension: LocalityDimension, allowed_values: Set[str]) -> Optional[bool]:
        """
        Three-valued residency helper: True (proven value is in allowed_values), False
        (proven value is present and NOT in allowed_values), or None (dimension is not
        proven -- caller MUST fail closed, never treat None as either True or False).
        This is intentionally the only "does this satisfy X" surface in this module;
        actual residency policy composition/enforcement is P7B.15's responsibility.
        """
        proven = self.proven_value_for(dimension)
        if proven is None:
            return None
        return proven in allowed_values


def new_locality_observed_at() -> str:
    return datetime.now(timezone.utc).isoformat()
