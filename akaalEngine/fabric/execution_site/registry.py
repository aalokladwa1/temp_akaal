"""
akaalEngine.fabric.execution_site.registry
=============================================
P7B.5 -- Execution Site registration/trust/assignment authority.

Every state transition that matters (identity verification, trust elevation, tenant
binding, execution assignment) requires an externally-supplied decision function
(`SiteIdentityVerifier` / an authorization callback) -- this registry never manufactures
its own "yes". This is the same fail-closed-delegation pattern as
akaalEngine.fabric.workload_identity.boundary.CloudAuthenticationBoundary, applied to
sites instead of cloud identities.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, runtime_checkable

from akaalEngine.fabric.execution_site.models import (
    ExecutionSite,
    SiteAssignment,
    SiteLifecycleState,
    SiteTrustState,
    trust_rank,
)


class SiteRegistryError(RuntimeError):
    pass


class UnknownSiteError(KeyError):
    """Fails safely for any unknown site_id -- never fabricates a default site."""


class SiteSelfElevationRejectedError(SiteRegistryError):
    """Raised when a registration attempts to pre-declare a trust_state above REGISTERED."""


class SiteIdentityCollisionError(SiteRegistryError):
    """Raised when a site_id is re-registered with different identity-defining fields
    (environment_id / claimed_security_identity) than its existing record -- prevents a
    second, unrelated physical site from hijacking an already-registered site_id."""


class StaleFencingError(SiteRegistryError):
    """Raised when an assignment's fencing_epoch does not strictly exceed the site's last epoch."""


class AssignmentAuthorizationDeniedError(SiteRegistryError):
    pass


@runtime_checkable
class SiteIdentityVerifier(Protocol):
    """Verifies a presented credential (e.g. an SPIFFE X.509/JWT SVID, or an mTLS peer
    certificate) actually proves the site's claimed_security_identity. Production callers
    supply an implementation wrapping their own cryptographic verifier (e.g.
    akaalPipeline.security.spiffe.SpiffeSVIDValidator) -- this registry never verifies
    cryptographic material itself, avoiding a second, divergent crypto-trust
    implementation."""

    def __call__(self, site: ExecutionSite, presented_credential: Any) -> bool: ...


@runtime_checkable
class SiteAuthorizationCallback(Protocol):
    """Decision function for trust elevation / tenant binding / execution assignment.
    Always the caller's responsibility (in production, backed by Pipeline's
    CentralAuthorizationEngine); this registry has no default-allow path."""

    def __call__(self, site: ExecutionSite, action: str, context: Mapping[str, Any]) -> bool: ...


class SiteRegistry:
    def __init__(self, durability_store: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._by_id: Dict[str, ExecutionSite] = {}
        self._last_epoch_by_site: Dict[str, int] = {}
        # Optional akaalEngine.fabric.durability.FabricDurabilityStore -- see
        # EnvironmentRegistry's identical field for the full rationale. When present,
        # site registration/trust/tenant-binding state AND the per-site fencing epoch
        # (replay protection) are persisted so a fresh process can reconstruct them via
        # akaalEngine.fabric.durability.reconstruct_site_registry.
        self._durability_store = durability_store

    def _persist_site(self, site: ExecutionSite) -> None:
        if self._durability_store is not None:
            self._durability_store.save_site(site)

    # ------------------------------------------------------------------
    # Registration -- never grants trust
    # ------------------------------------------------------------------

    def register(self, site: ExecutionSite) -> ExecutionSite:
        """
        A newly presented site can only ever enter as UNREGISTERED/REGISTERED -- any
        attempt to register with a higher pre-set trust_state is rejected outright
        (self-elevation is not merely ignored, it is a hard error so the caller notices
        their own bug/attack attempt).

        Round-2 hostile-review finding (P7B Group-1 §6 "site ID collision"): the first
        pass had NO collision check here at all -- re-registering an EXISTING site_id
        with a different claimed_security_identity/environment_id would silently
        overwrite the prior record, meaning a second, unrelated physical site could
        hijack an already-registered (possibly already-TRUSTED) site_id merely by
        registering under the same string. Closed: re-registration of an existing
        site_id is only accepted when its identity-defining fields
        (environment_id, claimed_security_identity) are unchanged; any TRUSTED/
        tenant-bound site attempting to be "re-registered" with different identity
        fields is rejected outright rather than silently downgraded and overwritten.
        """
        with self._lock:
            if trust_rank(site.trust_state) > trust_rank(SiteTrustState.REGISTERED):
                raise SiteSelfElevationRejectedError(
                    f"Site {site.site_id!r} attempted to register with trust_state "
                    f"{site.trust_state.value!r}; a site can never self-declare a trust "
                    f"level above REGISTERED."
                )

            existing = self._by_id.get(site.site_id)
            if existing is not None and (
                existing.environment_id != site.environment_id
                or existing.claimed_security_identity != site.claimed_security_identity
            ):
                raise SiteIdentityCollisionError(
                    f"site_id {site.site_id!r} is already registered with "
                    f"environment_id={existing.environment_id!r} / "
                    f"claimed_security_identity={existing.claimed_security_identity!r}; "
                    f"refusing to silently overwrite it with a different physical "
                    f"identity (environment_id={site.environment_id!r} / "
                    f"claimed_security_identity={site.claimed_security_identity!r})."
                )

            normalized = self._with(site, trust_state=SiteTrustState.REGISTERED, tenant_binding=None)
            self._by_id[site.site_id] = normalized
            self._persist_site(normalized)
            return normalized

    def _register_reconstructed(self, site: ExecutionSite) -> ExecutionSite:
        """INTERNAL ONLY -- used exclusively by
        akaalEngine.fabric.durability.reconstruct_site_registry to rehydrate
        already-authoritative durable state (including a legitimately-elevated
        trust_state/tenant_binding) after a fresh-process restart. Bypasses the
        REGISTERED-ceiling check in register() for the same reason
        EnvironmentRegistry._register_reconstructed does -- rehydration is not a new,
        untrusted claim. Never call this with caller-supplied/untrusted input."""
        with self._lock:
            self._by_id[site.site_id] = site
            return site

    def _restore_fencing_epoch(self, site_id: str, epoch: int) -> None:
        """INTERNAL ONLY -- restores the last-consumed fencing epoch after a fresh-process
        restart so a restarted control plane cannot reissue an already-consumed epoch
        (replay protection must survive restart)."""
        with self._lock:
            self._last_epoch_by_site[site_id] = epoch

    def get(self, site_id: str) -> ExecutionSite:
        with self._lock:
            site = self._by_id.get(site_id)
            if site is None:
                raise UnknownSiteError(f"Unknown site_id: {site_id!r}")
            return site

    def try_get(self, site_id: str) -> Optional[ExecutionSite]:
        with self._lock:
            return self._by_id.get(site_id)

    def list_sites(self) -> List[ExecutionSite]:
        with self._lock:
            return list(self._by_id.values())

    @staticmethod
    def _with(site: ExecutionSite, **overrides: Any) -> ExecutionSite:
        fields = {
            "site_id": site.site_id,
            "site_kind": site.site_kind,
            "environment_id": site.environment_id,
            "display_name": site.display_name,
            "geography": site.geography,
            "region": site.region,
            "availability_zone": site.availability_zone,
            "network_membership": site.network_membership,
            "capabilities": site.capabilities,
            "worker_pool_refs": site.worker_pool_refs,
            "reachable_endpoint_refs": site.reachable_endpoint_refs,
            "staging_capable": site.staging_capable,
            "claimed_security_identity": site.claimed_security_identity,
            "health_state": site.health_state,
            "trust_state": site.trust_state,
            "policy_labels": site.policy_labels,
            "runtime_characteristics": site.runtime_characteristics,
            "lifecycle_state": site.lifecycle_state,
            "tenant_binding": site.tenant_binding,
            "registered_at": site.registered_at,
        }
        fields.update(overrides)
        return ExecutionSite(**fields)

    # ------------------------------------------------------------------
    # Identity verification -- registration != trust, step 2 of the ladder
    # ------------------------------------------------------------------

    def verify_identity(
        self,
        site_id: str,
        verifier: SiteIdentityVerifier,
        presented_credential: Any,
    ) -> ExecutionSite:
        with self._lock:
            site = self.get(site_id)
            if site.trust_state == SiteTrustState.REVOKED:
                raise SiteRegistryError(f"Site {site_id!r} is REVOKED; cannot re-verify identity.")
            if site.claimed_security_identity is None:
                raise SiteRegistryError(f"Site {site_id!r} has no claimed_security_identity to verify against.")

            verified = verifier(site, presented_credential)
            if not isinstance(verified, bool):
                raise SiteRegistryError("SiteIdentityVerifier must return an explicit bool.")
            if not verified:
                raise SiteRegistryError(f"Identity verification failed for site {site_id!r}.")

            updated = self._with(site, trust_state=SiteTrustState.IDENTITY_VERIFIED)
            self._by_id[site_id] = updated
            self._persist_site(updated)
            return updated

    # ------------------------------------------------------------------
    # Trust elevation -- step 3; requires explicit authorization, never internal
    # ------------------------------------------------------------------

    def elevate_to_trusted(
        self,
        site_id: str,
        authorization_callback: Optional[SiteAuthorizationCallback],
        context: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionSite:
        with self._lock:
            site = self.get(site_id)
            if site.trust_state != SiteTrustState.IDENTITY_VERIFIED:
                raise SiteRegistryError(
                    f"Site {site_id!r} must reach IDENTITY_VERIFIED before TRUSTED; "
                    f"current state is {site.trust_state.value!r}."
                )
            if authorization_callback is None:
                raise SiteRegistryError(
                    f"No SiteAuthorizationCallback supplied; a site can never self-grant "
                    f"TRUSTED status."
                )
            decision = authorization_callback(site, "elevate_to_trusted", context or {})
            if not isinstance(decision, bool):
                raise SiteRegistryError("SiteAuthorizationCallback must return an explicit bool.")
            if not decision:
                raise AssignmentAuthorizationDeniedError(f"Trust elevation denied for site {site_id!r}.")

            updated = self._with(site, trust_state=SiteTrustState.TRUSTED)
            self._by_id[site_id] = updated
            self._persist_site(updated)
            return updated

    def revoke(self, site_id: str, *, reason: str) -> ExecutionSite:
        """Revocation is always permitted without an authorization callback -- fail-closed
        actions never need extra permission; only fail-open (elevating) actions do."""
        if not reason or not reason.strip():
            raise SiteRegistryError("Revocation requires a non-empty reason for audit.")
        with self._lock:
            site = self.get(site_id)
            updated = self._with(site, trust_state=SiteTrustState.REVOKED, tenant_binding=None)
            self._by_id[site_id] = updated
            self._persist_site(updated)
            return updated

    # ------------------------------------------------------------------
    # Tenant binding -- a site cannot self-grant tenant access
    # ------------------------------------------------------------------

    def bind_tenant(
        self,
        site_id: str,
        tenant_id: str,
        authorization_callback: Optional[SiteAuthorizationCallback],
        context: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionSite:
        with self._lock:
            site = self.get(site_id)
            if site.trust_state != SiteTrustState.TRUSTED:
                raise SiteRegistryError(f"Site {site_id!r} must be TRUSTED before tenant binding; got {site.trust_state.value!r}.")
            if authorization_callback is None:
                raise SiteRegistryError("No SiteAuthorizationCallback supplied; a site can never self-bind a tenant.")
            decision = authorization_callback(site, "bind_tenant", {**(context or {}), "tenant_id": tenant_id})
            if not isinstance(decision, bool) or not decision:
                raise AssignmentAuthorizationDeniedError(f"Tenant binding denied for site {site_id!r} -> tenant {tenant_id!r}.")

            updated = self._with(site, tenant_binding=tenant_id, lifecycle_state=SiteLifecycleState.ACTIVE)
            self._by_id[site_id] = updated
            self._persist_site(updated)
            return updated

    # ------------------------------------------------------------------
    # Execution assignment -- a site cannot self-assign; stale fencing must not execute
    # ------------------------------------------------------------------

    def assign_execution(
        self,
        assignment: SiteAssignment,
        authorization_callback: Optional[SiteAuthorizationCallback],
        context: Optional[Mapping[str, Any]] = None,
    ) -> SiteAssignment:
        with self._lock:
            site = self.get(assignment.site_id)

            if not site.is_execution_authorized():
                raise SiteRegistryError(
                    f"Site {assignment.site_id!r} is not execution-ready (trust_state="
                    f"{site.trust_state.value!r}, tenant_binding={site.tenant_binding!r}, "
                    f"lifecycle_state={site.lifecycle_state.value!r})."
                )
            if site.tenant_binding != assignment.tenant_id:
                raise SiteRegistryError(
                    f"Site {assignment.site_id!r} is bound to tenant {site.tenant_binding!r}, "
                    f"not {assignment.tenant_id!r}; refusing cross-tenant assignment."
                )

            last_epoch = self._last_epoch_by_site.get(assignment.site_id, 0)
            if assignment.fencing_epoch <= last_epoch:
                raise StaleFencingError(
                    f"Assignment fencing_epoch {assignment.fencing_epoch} does not exceed "
                    f"site {assignment.site_id!r}'s last recorded epoch {last_epoch}; stale "
                    f"or replayed assignment refused."
                )

            if authorization_callback is None:
                raise SiteRegistryError("No SiteAuthorizationCallback supplied; a site can never self-assign execution work.")
            decision = authorization_callback(
                site,
                "assign_execution",
                {**(context or {}), "plan_id": assignment.plan_id, "migration_id": assignment.migration_id},
            )
            if not isinstance(decision, bool) or not decision:
                raise AssignmentAuthorizationDeniedError(f"Execution assignment denied for site {assignment.site_id!r}.")

            self._last_epoch_by_site[assignment.site_id] = assignment.fencing_epoch
            if self._durability_store is not None:
                self._durability_store.save_fencing_epoch(assignment.site_id, assignment.fencing_epoch)
            return assignment


default_site_registry = SiteRegistry()
