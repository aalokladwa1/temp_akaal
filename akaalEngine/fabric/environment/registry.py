"""
akaalEngine.fabric.environment.registry
=========================================
P7B.1 -- Environment registration seam.

CRITICAL LAW: registration is bookkeeping, not authorization and not trust. Registering
an Environment (or looking one up by id) never grants AKAAL execution permission over it
and never elevates its trust_state. The only thing this registry does is: (a) prevent two
different physical boundaries from silently colliding under one environment_id, and
(b) prevent the same physical cloud boundary from being registered twice under different
ids (which would let a caller "shop" for a fresh, untrusted locator pointing at an
already-known resource). Actual AKAAL authorization remains
akaalPipeline.security.central_authorization's responsibility; this module is never
consulted for an authorization decision.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.fabric.environment.models import (
    Environment,
    EnvironmentTrustState,
)


class EnvironmentRegistrationError(ValueError):
    """Raised when an Environment registration is rejected."""


class DuplicateEnvironmentIdentityError(EnvironmentRegistrationError):
    """Raised when environment_id collides with a different physical boundary, or vice versa."""


class EnvironmentSelfElevationRejectedError(EnvironmentRegistrationError):
    """Raised when a caller attempts to register an Environment with a pre-declared
    trust_state above UNKNOWN. (Round-2 hostile-review finding: the first pass only
    enforced this for ExecutionSite, not Environment -- an inconsistency that would have
    let a caller self-declare VERIFIED trust merely by constructing the dataclass with
    that value and calling register(). Closed here for parity with SiteRegistry.)"""


class UnknownEnvironmentError(KeyError):
    """Raised when an environment_id is not registered. Fails safely (never fabricates a default)."""


class EnvironmentRegistry:
    """Thread-safe, in-memory Environment registration/lookup authority."""

    def __init__(self, durability_store: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._by_id: Dict[str, Environment] = {}
        self._by_native_key: Dict[Tuple[str, ...], str] = {}
        # Optional akaalEngine.fabric.durability.FabricDurabilityStore -- when supplied,
        # every state-changing call also persists through the canonical durability
        # backend so a fresh process can reconstruct this registry's authoritative state
        # (registration + trust_state) rather than starting from a blank slate. Never
        # required -- callers that don't need cross-restart durability may omit it.
        self._durability_store = durability_store

    def register(self, env: Environment) -> Environment:
        """
        Registers an Environment. Idempotent for an exact re-registration of the same
        (environment_id, physical boundary) pair; rejects any collision where the same
        environment_id or the same physical boundary would otherwise resolve inconsistently.
        Never elevates trust_state as a side effect of registration -- a caller presenting
        a pre-declared trust_state above UNKNOWN is rejected outright (self-elevation is a
        hard error, not silently downgraded, so the caller notices their own bug/attack).
        """
        with self._lock:
            if env.trust_state != EnvironmentTrustState.UNKNOWN:
                raise EnvironmentSelfElevationRejectedError(
                    f"Environment {env.environment_id!r} attempted to register with "
                    f"trust_state {env.trust_state.value!r}; a caller can never self-declare "
                    f"a trust level above UNKNOWN at registration time."
                )

            native_key = env.native_key()

            existing_by_id = self._by_id.get(env.environment_id)
            if existing_by_id is not None and existing_by_id.native_key() != native_key:
                raise DuplicateEnvironmentIdentityError(
                    f"environment_id {env.environment_id!r} is already registered against a "
                    f"different physical boundary {existing_by_id.native_key()!r}; refusing to "
                    f"silently repoint an existing locator at {native_key!r}."
                )

            existing_id_for_native = self._by_native_key.get(native_key)
            if existing_id_for_native is not None and existing_id_for_native != env.environment_id:
                raise DuplicateEnvironmentIdentityError(
                    f"Physical boundary {native_key!r} is already registered under "
                    f"environment_id {existing_id_for_native!r}; cannot register a second, "
                    f"distinct locator {env.environment_id!r} for the same physical boundary."
                )

            self._by_id[env.environment_id] = env
            self._by_native_key[native_key] = env.environment_id
            if self._durability_store is not None:
                self._durability_store.save_environment(env)
            return env

    def _register_reconstructed(self, env: Environment) -> Environment:
        """
        INTERNAL ONLY -- used exclusively by
        akaalEngine.fabric.durability.reconstruct_environment_registry to rehydrate
        already-authoritative durable state (including a legitimately-elevated
        trust_state that was previously granted via elevate_trust and persisted) after a
        fresh-process restart. This deliberately bypasses the UNKNOWN-only check in
        register() -- that check exists to stop a NEW, untrusted claim, not to erase
        trust the registry itself already granted and durably recorded before the
        restart. Never call this with caller-supplied/untrusted input.
        """
        with self._lock:
            native_key = env.native_key()
            self._by_id[env.environment_id] = env
            self._by_native_key[native_key] = env.environment_id
            return env

    def get(self, environment_id: str) -> Environment:
        """Fails safely (raises) for any unknown environment_id -- never fabricates a default."""
        with self._lock:
            env = self._by_id.get(environment_id)
            if env is None:
                raise UnknownEnvironmentError(f"Unknown environment_id: {environment_id!r}")
            return env

    def try_get(self, environment_id: str) -> Optional[Environment]:
        with self._lock:
            return self._by_id.get(environment_id)

    def is_registered(self, environment_id: str) -> bool:
        with self._lock:
            return environment_id in self._by_id

    def get_trust_state(self, environment_id: str) -> EnvironmentTrustState:
        """Returns the current trust_state. This is informational data ONLY -- callers must
        still go through akaalPipeline.security.central_authorization for any authorization
        decision; a REGISTERED or even VERIFIED trust_state is never itself a grant."""
        return self.get(environment_id).trust_state

    def elevate_trust(
        self,
        environment_id: str,
        new_state: EnvironmentTrustState,
        *,
        reason: str,
    ) -> Environment:
        """
        Explicitly elevates (or revokes) an Environment's trust_state. This is a deliberate,
        auditable, out-of-band action -- never a side effect of lookup, registration, or
        any cloud-native authentication event. Revocation is always permitted; elevation to
        VERIFIED must be called by an authorized caller (enforced by the caller's own
        AKAAL-authorization check upstream of this method -- this registry does not itself
        perform that check, to avoid duplicating the authorization authority).
        """
        with self._lock:
            env = self.get(environment_id)
            if not reason or not reason.strip():
                raise EnvironmentRegistrationError("Trust state changes require a non-empty reason for audit.")
            updated = Environment(
                environment_id=env.environment_id,
                environment_type=env.environment_type,
                boundary=env.boundary,
                display_name=env.display_name,
                geography=env.geography,
                region=env.region,
                availability_zone=env.availability_zone,
                networks=env.networks,
                execution_site_ids=env.execution_site_ids,
                storage_resource_ids=env.storage_resource_ids,
                capabilities=env.capabilities,
                policy_attributes=env.policy_attributes,
                trust_state=new_state,
                native_resource_refs=env.native_resource_refs,
                lifecycle_state=env.lifecycle_state,
                jurisdiction=env.jurisdiction,
                provenance_source=env.provenance_source,
                registered_by=env.registered_by,
                registered_at=env.registered_at,
            )
            self._by_id[environment_id] = updated
            if self._durability_store is not None:
                self._durability_store.save_environment(updated)
            return updated

    def list_environments(self) -> List[Environment]:
        with self._lock:
            return list(self._by_id.values())


default_environment_registry = EnvironmentRegistry()
