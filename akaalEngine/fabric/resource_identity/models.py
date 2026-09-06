"""
akaalEngine.fabric.resource_identity.models
==============================================
P7B.2 -- Cloud Resource Identity & Discovery.

Preserves, as five strictly-ordered and never-conflated states:

    RESOURCE EXISTS != RESOURCE DISCOVERED != RESOURCE REACHABLE
        != RESOURCE AUTHORIZED != RESOURCE TRUSTED FOR EXECUTION

`ResourceProofLevel` is a strict ladder: a caller can never claim a higher proof level
than what the specific probe/verification that produced the `ResourceDiscoveryRecord`
actually established. Discovery adapters in this package are only ever capable of
producing up to `REACHABLE` -- `AUTHORIZED` and `TRUSTED_FOR_EXECUTION` require a
separate, explicit step outside of discovery (AKAAL authorization /
akaalEngine.fabric.execution_site trust), never inferred from a successful discovery
call alone.

Provider-native resource identity is preserved distinctly per cloud (ARN vs Azure
Resource ID vs GCP resource name vs OCID) -- never collapsed into one generic string
whose meaning depends on which cloud happens to be reading it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Mapping, Optional
from types import MappingProxyType


class ResourceProofLevel(IntEnum):
    """Strictly ordered. Higher values require everything the lower values require."""
    EXISTS = 1
    DISCOVERED = 2
    REACHABLE = 3
    AUTHORIZED = 4
    TRUSTED_FOR_EXECUTION = 5


class ResourceLocatorValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CloudResourceLocator:
    """Abstract marker base. Never instantiated directly -- use a provider-specific subclass."""

    def native_identifier(self) -> str:
        raise NotImplementedError

    def provider(self) -> str:
        raise NotImplementedError


# Round-3 hostile-review fix (P7B Group-1 §8): the original pattern hardcoded the
# "aws" partition (rejecting genuine "aws-cn"/"aws-us-gov"/"aws-iso"* ARNs -- a real
# under-validation-in-the-wrong-direction bug: legitimate provider-native identities
# were being rejected) and required a 12-digit account segment (rejecting genuine
# accountless global ARNs, e.g. "arn:aws:s3:::my-bucket", where S3's ARN format has no
# account segment at all). Both are now correctly permissive without weakening the
# actual security property (account/tenant cross-check remains enforced below, in
# __post_init__, precisely where an account segment IS present).
_ARN_RE = re.compile(r"^arn:aws(?:-[a-z]+){0,2}:[a-z0-9\-]+:[a-z0-9\-]*:(\d{12})?:.+$")
# Round-6 hostile-review fix (P7B Group-1 blocker #1): Azure Resource Manager treats
# the path KEYWORDS ("subscriptions"/"resourceGroups"/"providers") case-insensitively --
# different Azure API/CLI versions have been observed to return them in different
# casing (e.g. "resourcegroups" lowercase). The original pattern hardcoded exact case,
# rejecting genuine provider-native identities. `re.IGNORECASE` fixes this without
# weakening anything: the actual VALUES (subscription GUID, resource group name,
# provider namespace, resource path) are untouched by this flag and remain fully
# significant/case-preserved in the stored resource_id string.
_AZURE_RESOURCE_ID_RE = re.compile(r"^/subscriptions/([0-9a-fA-F\-]{36})/resourceGroups/[^/]+/providers/.+$", re.IGNORECASE)
_OCID_RESOURCE_RE = re.compile(r"^ocid1\.[a-z0-9_]+\.")


@dataclass(frozen=True)
class AWSResourceLocator(CloudResourceLocator):
    """AWS resources are identified by ARN -- the only truthful cross-service AWS identifier."""
    arn: str
    account_id: str
    region: Optional[str] = None

    def __post_init__(self) -> None:
        if not _ARN_RE.match(self.arn or ""):
            raise ResourceLocatorValidationError(f"Malformed AWS ARN: {self.arn!r}")
        arn_account = self.arn.split(":")[4]
        if arn_account and arn_account != self.account_id:
            raise ResourceLocatorValidationError(
                f"AWS ARN account segment {arn_account!r} does not match declared account_id "
                f"{self.account_id!r}; refusing to accept an inconsistent locator."
            )

    def native_identifier(self) -> str:
        return self.arn

    def provider(self) -> str:
        return "AWS"


@dataclass(frozen=True)
class AzureResourceLocator(CloudResourceLocator):
    """Azure resources are identified by the full Azure Resource ID path."""
    resource_id: str
    subscription_id: str

    def __post_init__(self) -> None:
        if not _AZURE_RESOURCE_ID_RE.match(self.resource_id or ""):
            raise ResourceLocatorValidationError(f"Malformed Azure resource id: {self.resource_id!r}")
        # Round-6 hostile-review fix, corrected twice in the same pass:
        #   1. Azure subscription GUIDs are hex and genuinely case-insensitive at the
        #      platform level -- comparison must be case-insensitive so a legitimately
        #      differently-cased GUID is not falsely rejected.
        #   2. A blanket substring check (even case-insensitive) is a REAL cross-
        #      subscription vulnerability: an attacker-influenceable segment elsewhere
        #      in the path (e.g. a resource GROUP NAME containing a victim's
        #      subscription GUID as literal text, such as
        #      "resourceGroups/rg-<victim-guid>-evil") would let a resource that is
        #      ACTUALLY in a completely different subscription pass this check. Fixed
        #      by extracting the ACTUAL subscription segment via the same anchored
        #      regex that already validates overall shape, and comparing ONLY that
        #      captured segment -- never a search anywhere in the full string.
        match = _AZURE_RESOURCE_ID_RE.match(self.resource_id)
        actual_subscription_segment = match.group(1) if match else None
        if actual_subscription_segment is None or actual_subscription_segment.lower() != self.subscription_id.lower():
            raise ResourceLocatorValidationError(
                f"Azure resource_id's actual subscription segment {actual_subscription_segment!r} "
                f"does not match declared subscription_id {self.subscription_id!r}; refusing to "
                f"accept an inconsistent locator."
            )

    def native_identifier(self) -> str:
        return self.resource_id

    def provider(self) -> str:
        return "AZURE"


@dataclass(frozen=True)
class GCPResourceLocator(CloudResourceLocator):
    """GCP resources are identified by their fully-qualified resource name."""
    resource_name: str
    project_id: str

    def __post_init__(self) -> None:
        if not self.resource_name or "/" not in self.resource_name:
            raise ResourceLocatorValidationError(f"Malformed GCP resource_name: {self.resource_name!r}")
        # Round-6 hostile-review fix (P7B Group-1 blocker #2): a bare substring check
        # (`f"projects/{project_id}" in resource_name`) is a REAL cross-project
        # confusion vulnerability -- "projects/proj1" is a textual PREFIX of
        # "projects/proj1-evil/...", so a resource genuinely in project "proj1-evil"
        # would incorrectly validate against a locator claiming project_id="proj1".
        # Fixed by requiring an exact path-SEGMENT match: split on "/" and verify
        # segments == ["projects", project_id, ...], not merely a substring anywhere.
        segments = self.resource_name.split("/")
        if len(segments) < 2 or segments[0] != "projects" or segments[1] != self.project_id:
            raise ResourceLocatorValidationError(
                f"GCP resource_name does not reference declared project_id {self.project_id!r}; "
                f"refusing to accept an inconsistent locator."
            )

    def native_identifier(self) -> str:
        return self.resource_name

    def provider(self) -> str:
        return "GCP"


@dataclass(frozen=True)
class OCIResourceLocator(CloudResourceLocator):
    """OCI resources are identified by OCID."""
    ocid: str
    compartment_ocid: str

    def __post_init__(self) -> None:
        if not _OCID_RESOURCE_RE.match(self.ocid or ""):
            raise ResourceLocatorValidationError(f"Malformed OCID: {self.ocid!r}")
        if not self.compartment_ocid.startswith("ocid1.compartment."):
            raise ResourceLocatorValidationError(
                f"OCI compartment_ocid must start with 'ocid1.compartment.'; got {self.compartment_ocid!r}"
            )

    def native_identifier(self) -> str:
        return self.ocid

    def provider(self) -> str:
        return "OCI"


@dataclass(frozen=True)
class ResourceDiscoveryRecord:
    """
    Immutable record of what has actually been established about a cloud resource.
    `proof_level` is the single source of truth for how far this record may be trusted;
    callers must never assume a proof level beyond what is recorded here.
    """
    locator: CloudResourceLocator
    proof_level: ResourceProofLevel
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resource_kind: str = "UNKNOWN"
    evidence: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    stale: bool = False

    def __post_init__(self) -> None:
        if self.proof_level >= ResourceProofLevel.AUTHORIZED:
            raise ResourceLocatorValidationError(
                "ResourceDiscoveryRecord may never itself carry AUTHORIZED or "
                "TRUSTED_FOR_EXECUTION proof -- those require a separate, explicit AKAAL "
                "authorization / execution-site trust decision outside of discovery."
            )
        if not isinstance(self.evidence, MappingProxyType):
            object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def at_least(self, level: ResourceProofLevel) -> bool:
        return (not self.stale) and self.proof_level >= level
