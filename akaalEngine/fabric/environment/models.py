"""
akaalEngine.fabric.environment.models
======================================
P7B.1 -- Canonical Environment Model.

An Environment represents a place where data resources and/or AKAAL execution capacity
can exist: on-premises, a private datacenter, AWS, Azure, GCP, OCI, Kubernetes, a VM
execution environment, or bare metal.

Absolute laws enforced here (P7B Group-1 security invariants):
    * Environment ID is a locator, not authorization (registration/lookup never implies
      permission -- see akaalEngine.fabric.environment.registry and
      akaalPipeline.security.central_authorization for the actual authorization boundary).
    * Cloud-provider semantics are never falsely normalized into one shape: an AWS account,
      an Azure subscription, a GCP project, and an OCI tenancy are represented as distinct,
      non-interchangeable boundary types (`CloudNativeBoundary` subclasses), each with its
      own truthful validation. There is no generic "account_id" field that silently accepts
      any provider's identifier.
    * Trust state defaults to UNKNOWN and is never auto-elevated by construction alone.
    * Jurisdiction is optional and is never inferred from region/geography -- it is only
      ever set explicitly by a caller who actually knows it.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import FrozenSet, Mapping, Optional, Tuple
from types import MappingProxyType


class EnvironmentType(str, Enum):
    ON_PREMISES = "ON_PREMISES"
    PRIVATE_DATACENTER = "PRIVATE_DATACENTER"
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"
    OCI = "OCI"
    KUBERNETES = "KUBERNETES"
    VM = "VM"
    BARE_METAL = "BARE_METAL"


class EnvironmentTrustState(str, Enum):
    """Trust is never implied by registration alone -- it must be explicitly elevated."""
    UNKNOWN = "UNKNOWN"
    REGISTERED = "REGISTERED"
    VERIFIED = "VERIFIED"
    REVOKED = "REVOKED"


class EnvironmentLifecycleState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DECOMMISSIONED = "DECOMMISSIONED"


class EnvironmentValidationError(ValueError):
    """Raised when an Environment or its boundary is malformed or internally inconsistent."""


# --------------------------------------------------------------------------------------
# Cloud-native boundary identity -- deliberately NOT unified into one generic field set.
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class CloudNativeBoundary:
    """Abstract marker base. Never instantiated directly."""

    def native_key(self) -> Tuple[str, ...]:
        raise NotImplementedError


_AWS_ACCOUNT_RE = re.compile(r"^\d{12}$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_OCID_RE = re.compile(r"^ocid1\.tenancy\.")


@dataclass(frozen=True)
class AWSBoundary(CloudNativeBoundary):
    """An AWS account boundary. Never conflated with an Azure subscription or GCP project."""
    account_id: str

    def __post_init__(self) -> None:
        if not _AWS_ACCOUNT_RE.match(self.account_id or ""):
            raise EnvironmentValidationError(
                f"AWS account_id must be exactly 12 digits; got {self.account_id!r}"
            )

    def native_key(self) -> Tuple[str, ...]:
        return ("AWS", self.account_id)


@dataclass(frozen=True)
class AzureBoundary(CloudNativeBoundary):
    """An Azure subscription boundary, optionally scoped under an Entra tenant."""
    subscription_id: str
    tenant_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not _UUID_RE.match(self.subscription_id or ""):
            raise EnvironmentValidationError(
                f"Azure subscription_id must be a valid UUID; got {self.subscription_id!r}"
            )
        if self.tenant_id is not None and not _UUID_RE.match(self.tenant_id):
            raise EnvironmentValidationError(
                f"Azure tenant_id, if provided, must be a valid UUID; got {self.tenant_id!r}"
            )

    def native_key(self) -> Tuple[str, ...]:
        return ("AZURE", self.subscription_id)


@dataclass(frozen=True)
class GCPBoundary(CloudNativeBoundary):
    """A GCP project boundary, optionally scoped under a GCP organization."""
    project_id: str
    organization_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Round-3 hostile-review fix (P7B Group-1 §10): GCP genuinely has two distinct,
        # both-legitimate identifiers for the same project boundary -- the human-readable
        # project ID (letters/digits/hyphens) and the numeric project NUMBER (some
        # discovery/resource-name paths surface the number, not the ID). The original
        # validator only accepted the ID form, which would falsely reject a truthful
        # project number returned by a real GCP API. Both forms are accepted here, but
        # they are never silently treated as interchangeable with each other elsewhere --
        # native_key() uses whichever form was actually supplied, so a project registered
        # by ID and the same project later referenced by number would correctly be
        # treated as two DIFFERENT locators (no false cross-form equivalence is created).
        is_project_id = bool(re.match(r"^[a-z][a-z0-9\-]{4,28}[a-z0-9]$", self.project_id or ""))
        is_project_number = bool(re.match(r"^\d{1,30}$", self.project_id or ""))
        if not (is_project_id or is_project_number):
            raise EnvironmentValidationError(
                f"GCP project_id must be a valid GCP project ID string or a numeric "
                f"project number; got {self.project_id!r}"
            )

    def native_key(self) -> Tuple[str, ...]:
        return ("GCP", self.project_id)


@dataclass(frozen=True)
class OCIBoundary(CloudNativeBoundary):
    """An OCI tenancy boundary, optionally scoped to a compartment."""
    tenancy_ocid: str
    compartment_ocid: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.tenancy_ocid.startswith("ocid1.tenancy."):
            raise EnvironmentValidationError(
                f"OCI tenancy_ocid must start with 'ocid1.tenancy.'; got {self.tenancy_ocid!r}"
            )
        if self.compartment_ocid is not None and not self.compartment_ocid.startswith("ocid1.compartment."):
            raise EnvironmentValidationError(
                f"OCI compartment_ocid, if provided, must start with 'ocid1.compartment.'; got {self.compartment_ocid!r}"
            )

    def native_key(self) -> Tuple[str, ...]:
        return ("OCI", self.tenancy_ocid)


@dataclass(frozen=True)
class OnPremBoundary(CloudNativeBoundary):
    """An on-premises / private-datacenter organizational boundary."""
    organization_unit: str
    facility_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.organization_unit or not self.organization_unit.strip():
            raise EnvironmentValidationError("On-prem organization_unit must be a non-empty string.")

    def native_key(self) -> Tuple[str, ...]:
        return ("ONPREM", self.organization_unit, self.facility_id or "")


@dataclass(frozen=True)
class KubernetesBoundary(CloudNativeBoundary):
    """A Kubernetes cluster boundary. Kubernetes is one Execution Site implementation, not
    a universal AKAAL runtime requirement -- see akaalEngine.fabric.execution_site."""
    cluster_name: str
    cluster_uid: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.cluster_name or not self.cluster_name.strip():
            raise EnvironmentValidationError("Kubernetes cluster_name must be a non-empty string.")

    def native_key(self) -> Tuple[str, ...]:
        return ("KUBERNETES", self.cluster_uid or self.cluster_name)


@dataclass(frozen=True)
class GenericExecutionBoundary(CloudNativeBoundary):
    """Boundary for bare-metal/VM execution environments not owned by a cloud account."""
    owner_reference: str

    def __post_init__(self) -> None:
        if not self.owner_reference or not self.owner_reference.strip():
            raise EnvironmentValidationError("GenericExecutionBoundary owner_reference must be non-empty.")

    def native_key(self) -> Tuple[str, ...]:
        return ("GENERIC", self.owner_reference)


_BOUNDARY_TYPE_FOR_ENVIRONMENT: Mapping[EnvironmentType, type] = {
    EnvironmentType.AWS: AWSBoundary,
    EnvironmentType.AZURE: AzureBoundary,
    EnvironmentType.GCP: GCPBoundary,
    EnvironmentType.OCI: OCIBoundary,
    EnvironmentType.ON_PREMISES: OnPremBoundary,
    EnvironmentType.PRIVATE_DATACENTER: OnPremBoundary,
    EnvironmentType.KUBERNETES: KubernetesBoundary,
    EnvironmentType.VM: GenericExecutionBoundary,
    EnvironmentType.BARE_METAL: GenericExecutionBoundary,
}


@dataclass(frozen=True)
class NetworkSubnet:
    subnet_id: str
    cidr: Optional[str] = None
    is_private: bool = True

    def __post_init__(self) -> None:
        if not self.subnet_id or not self.subnet_id.strip():
            raise EnvironmentValidationError("NetworkSubnet.subnet_id must be non-empty.")


@dataclass(frozen=True)
class Environment:
    """
    Canonical, immutable representation of a place where resources and/or AKAAL execution
    capacity can exist. Construction alone establishes NO authorization and NO trust --
    see akaalEngine.fabric.environment.registry.EnvironmentRegistry for the registration
    seam, and akaalPipeline.security.central_authorization for actual AKAAL authorization.
    """
    environment_id: str
    environment_type: EnvironmentType
    boundary: CloudNativeBoundary
    display_name: str = ""
    geography: Optional[str] = None
    region: Optional[str] = None
    availability_zone: Optional[str] = None
    networks: Tuple[NetworkSubnet, ...] = field(default_factory=tuple)
    execution_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    storage_resource_ids: Tuple[str, ...] = field(default_factory=tuple)
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
    policy_attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    trust_state: EnvironmentTrustState = EnvironmentTrustState.UNKNOWN
    native_resource_refs: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    lifecycle_state: EnvironmentLifecycleState = EnvironmentLifecycleState.PROVISIONAL
    # Jurisdiction is optional and NEVER inferred -- only set when a caller truthfully knows it.
    jurisdiction: Optional[str] = None
    provenance_source: str = "UNKNOWN"
    registered_by: Optional[str] = None
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.environment_id or not self.environment_id.strip():
            raise EnvironmentValidationError("Environment.environment_id must be a non-empty string.")

        expected_boundary_type = _BOUNDARY_TYPE_FOR_ENVIRONMENT.get(self.environment_type)
        if expected_boundary_type is None:
            raise EnvironmentValidationError(f"Unrecognized environment_type: {self.environment_type!r}")
        if not isinstance(self.boundary, expected_boundary_type):
            raise EnvironmentValidationError(
                f"Environment of type {self.environment_type.value} requires a "
                f"{expected_boundary_type.__name__} boundary; got {type(self.boundary).__name__}. "
                f"Cloud-provider boundary semantics are never normalized into a generic shape."
            )

        if not isinstance(self.networks, tuple):
            object.__setattr__(self, "networks", tuple(self.networks))
        if not isinstance(self.execution_site_ids, tuple):
            object.__setattr__(self, "execution_site_ids", tuple(self.execution_site_ids))
        if not isinstance(self.storage_resource_ids, tuple):
            object.__setattr__(self, "storage_resource_ids", tuple(self.storage_resource_ids))
        if not isinstance(self.capabilities, frozenset):
            object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        if not isinstance(self.policy_attributes, MappingProxyType):
            object.__setattr__(self, "policy_attributes", MappingProxyType(dict(self.policy_attributes)))
        if not isinstance(self.native_resource_refs, MappingProxyType):
            object.__setattr__(self, "native_resource_refs", MappingProxyType(dict(self.native_resource_refs)))

    def native_key(self) -> Tuple[str, ...]:
        """Deterministic dedupe key derived from the *physical* boundary, never the environment_id."""
        return self.boundary.native_key()

    def to_dict(self) -> dict:
        return {
            "environment_id": self.environment_id,
            "environment_type": self.environment_type.value,
            "boundary": {"type": type(self.boundary).__name__, **self.boundary.__dict__},
            "display_name": self.display_name,
            "geography": self.geography,
            "region": self.region,
            "availability_zone": self.availability_zone,
            "networks": [n.__dict__ for n in self.networks],
            "execution_site_ids": list(self.execution_site_ids),
            "storage_resource_ids": list(self.storage_resource_ids),
            "capabilities": sorted(self.capabilities),
            "policy_attributes": dict(self.policy_attributes),
            "trust_state": self.trust_state.value,
            "native_resource_refs": dict(self.native_resource_refs),
            "lifecycle_state": self.lifecycle_state.value,
            "jurisdiction": self.jurisdiction,
            "provenance_source": self.provenance_source,
            "registered_by": self.registered_by,
            "registered_at": self.registered_at,
        }


def new_environment_id(environment_type: EnvironmentType) -> str:
    """Generates a collision-resistant environment_id. This is a LOCATOR, not an authorization token."""
    return f"env-{environment_type.value.lower()}-{uuid.uuid4().hex[:16]}"
