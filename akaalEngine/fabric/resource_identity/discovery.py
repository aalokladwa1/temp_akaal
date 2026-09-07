"""
akaalEngine.fabric.resource_identity.discovery
=================================================
P7B.2 -- Per-cloud resource discovery adapters.

Each adapter is gated on its cloud SDK being installed (boto3 / azure-mgmt-resource /
google-cloud-resource-manager / oci) and fails closed with `DiscoveryDependencyMissing`
when it is not -- never fabricates a discovery result. Every adapter can only ever
produce up to `ResourceProofLevel.REACHABLE`; `AUTHORIZED` and `TRUSTED_FOR_EXECUTION`
are never granted here (see models.py).

These adapters intentionally do not attempt full pagination/throttling-resilient
production behavior beyond what a single hostile-tested code path can prove locally
without live cloud credentials -- LIVE_PROVEN behavior against a real account is
EXTERNAL_DEFERRED (see progress.md P7B Group-1 proof model).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from akaalEngine.fabric.resource_identity.models import (
    AWSResourceLocator,
    AzureResourceLocator,
    CloudResourceLocator,
    GCPResourceLocator,
    OCIResourceLocator,
    ResourceDiscoveryRecord,
    ResourceProofLevel,
)

logger = logging.getLogger("akaalEngine.fabric.resource_identity.discovery")


class DiscoveryDependencyMissing(RuntimeError):
    """Raised when a cloud discovery adapter's SDK dependency is not installed."""


class DiscoveryDenied(RuntimeError):
    """Raised when a cloud API call for discovery fails due to permission denial (fails closed,
    never silently downgraded into a fabricated 'not found')."""


class DiscoveryThrottled(RuntimeError):
    """Raised when a cloud API call for discovery is throttled/rate-limited."""


class DiscoveryUnavailable(RuntimeError):
    """Raised when the cloud provider API itself is unreachable/unavailable."""


@dataclass(frozen=True)
class DiscoveryOutcome:
    """Result of an attempted discovery call: either a truthful record or a truthful failure."""
    record: Optional[ResourceDiscoveryRecord]
    error: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.record is not None


def _dependency_check(module_name: str) -> None:
    try:
        __import__(module_name)
    except ImportError as exc:
        raise DiscoveryDependencyMissing(
            f"'{module_name}' is not installed; cannot perform live cloud discovery. "
            f"Install it to enable this adapter."
        ) from exc


def discover_aws_resource(locator: AWSResourceLocator, sts_client=None) -> DiscoveryOutcome:
    """
    Confirms the AWS account referenced by `locator` is genuinely reachable via STS
    GetCallerIdentity (a real, cheap, universally-permitted AWS API call), truthfully
    distinguishing EXISTS (locator is well-formed) from REACHABLE (the AWS API answered).
    A caller may inject a pre-built boto3 STS client (`sts_client`) for testing without a
    live AWS account; production code should not pass one and rely on ambient credentials.
    """
    if sts_client is None:
        _dependency_check("boto3")
        import boto3
        sts_client = boto3.client("sts", region_name=locator.region or "us-east-1")

    try:
        identity = sts_client.get_caller_identity()
    except Exception as exc:
        msg = str(exc)
        if "AccessDenied" in msg or "UnauthorizedAccess" in msg:
            raise DiscoveryDenied(f"AWS STS GetCallerIdentity denied: {msg}") from exc
        if "Throttling" in msg or "TooManyRequests" in msg:
            raise DiscoveryThrottled(f"AWS STS throttled: {msg}") from exc
        raise DiscoveryUnavailable(f"AWS STS call failed: {msg}") from exc

    reachable_account = identity.get("Account")
    if reachable_account != locator.account_id:
        # This is exactly the "wrong account" hostile case: the reachable identity does not
        # match the locator's declared account -- fail closed, never proceed as if it matched.
        raise DiscoveryDenied(
            f"Live AWS identity resolved to account {reachable_account!r}, which does not "
            f"match the locator's declared account_id {locator.account_id!r}."
        )

    return DiscoveryOutcome(
        record=ResourceDiscoveryRecord(
            locator=locator,
            proof_level=ResourceProofLevel.REACHABLE,
            resource_kind="aws_generic_resource",
            evidence={"caller_identity_arn": identity.get("Arn", "")},
        )
    )


def discover_azure_resource(locator: AzureResourceLocator, resource_client=None) -> DiscoveryOutcome:
    """Confirms an Azure resource is reachable via Resource Manager `resources.get_by_id`."""
    if resource_client is None:
        _dependency_check("azure.mgmt.resource")
        raise DiscoveryDependencyMissing(
            "No azure ResourceManagementClient instance supplied; production discovery "
            "requires an authenticated client constructed by the caller's Azure workload "
            "identity flow (see akaalEngine.fabric.workload_identity)."
        )

    try:
        resource = resource_client.resources.get_by_id(locator.resource_id, api_version="2021-04-01")
    except Exception as exc:
        msg = str(exc)
        if "AuthorizationFailed" in msg or "Forbidden" in msg:
            raise DiscoveryDenied(f"Azure resource discovery denied: {msg}") from exc
        if "ResourceNotFound" in msg or "NotFound" in msg:
            raise DiscoveryUnavailable(f"Azure resource not found: {msg}") from exc
        if "TooManyRequests" in msg:
            raise DiscoveryThrottled(f"Azure discovery throttled: {msg}") from exc
        raise DiscoveryUnavailable(f"Azure resource discovery failed: {msg}") from exc

    return DiscoveryOutcome(
        record=ResourceDiscoveryRecord(
            locator=locator,
            proof_level=ResourceProofLevel.REACHABLE,
            resource_kind=getattr(resource, "type", "azure_generic_resource"),
            evidence={"provisioning_state": str(getattr(resource, "properties", {}))[:200]},
        )
    )


def discover_gcp_resource(locator: GCPResourceLocator, client=None) -> DiscoveryOutcome:
    """Confirms a GCP resource is reachable via an injected client's `.get()`-shaped call."""
    if client is None:
        raise DiscoveryDependencyMissing(
            "No GCP client instance supplied; production discovery requires an ADC/WIF- "
            "authenticated client constructed by the caller (see akaalEngine.fabric.workload_identity)."
        )
    try:
        resource = client.get(name=locator.resource_name)
    except Exception as exc:
        msg = str(exc)
        if "PermissionDenied" in msg or "403" in msg:
            raise DiscoveryDenied(f"GCP resource discovery denied: {msg}") from exc
        if "NotFound" in msg or "404" in msg:
            raise DiscoveryUnavailable(f"GCP resource not found: {msg}") from exc
        if "ResourceExhausted" in msg or "429" in msg:
            raise DiscoveryThrottled(f"GCP discovery throttled: {msg}") from exc
        raise DiscoveryUnavailable(f"GCP resource discovery failed: {msg}") from exc

    return DiscoveryOutcome(
        record=ResourceDiscoveryRecord(
            locator=locator,
            proof_level=ResourceProofLevel.REACHABLE,
            resource_kind="gcp_generic_resource",
            evidence={"resource_repr": str(resource)[:200]},
        )
    )


def discover_oci_resource(locator: OCIResourceLocator, client=None) -> DiscoveryOutcome:
    """Confirms an OCI resource is reachable via an injected client's `.get_resource()`-shaped call."""
    if client is None:
        _dependency_check("oci")
        raise DiscoveryDependencyMissing(
            "No OCI client instance supplied; production discovery requires an "
            "instance-principal/resource-principal-authenticated client constructed by the "
            "caller (see akaalEngine.fabric.workload_identity)."
        )
    try:
        response = client.get_resource(locator.ocid)
    except Exception as exc:
        status = getattr(exc, "status", None)
        if status == 401 or status == 403:
            raise DiscoveryDenied(f"OCI resource discovery denied: {exc}") from exc
        if status == 404:
            raise DiscoveryUnavailable(f"OCI resource not found: {exc}") from exc
        if status == 429:
            raise DiscoveryThrottled(f"OCI discovery throttled: {exc}") from exc
        raise DiscoveryUnavailable(f"OCI resource discovery failed: {exc}") from exc

    return DiscoveryOutcome(
        record=ResourceDiscoveryRecord(
            locator=locator,
            proof_level=ResourceProofLevel.REACHABLE,
            resource_kind="oci_generic_resource",
            evidence={"compartment_ocid": locator.compartment_ocid},
        )
    )
