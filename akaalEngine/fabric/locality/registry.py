"""
akaalEngine.fabric.locality.registry
=======================================
P7B.12 -- Locality registration/query seam.

Bookkeeping only, exactly like every other fabric registry: registering a LocalityRecord
never grants trust or authorization, and a PROVEN confidence recorded here is only ever as
trustworthy as the caller who supplied it -- this registry does not itself verify
locality claims (that is the responsibility of whatever discovery/probe mechanism
produced the record before calling `register`). Cross-tenant reads are refused outright.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.fabric.locality.models import (
    LocalityRecord,
    LocalitySubjectRole,
    LocalityValidationError,
)


class LocalityRegistrationError(LocalityValidationError):
    pass


class CrossTenantLocalityError(LocalityRegistrationError):
    pass


class UnknownLocalityError(KeyError):
    """Raised when no LocalityRecord exists for a (subject_ref, subject_role, tenant_id)
    key. Fails safely -- never fabricates an UNKNOWN-confidence default record, because a
    caller distinguishing 'never observed' from 'observed and genuinely unknown' matters
    for audit."""


_Key = Tuple[str, str, str]  # (tenant_id, subject_ref, subject_role.value)


class LocalityRegistry:
    """Thread-safe, tenant-scoped locality registration/query authority. Keeps the full
    history per (tenant, subject_ref, subject_role) key so re-observation never silently
    destroys the audit trail of what was previously believed."""

    def __init__(self, durability_store: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._current: Dict[_Key, LocalityRecord] = {}
        self._history: Dict[_Key, List[LocalityRecord]] = {}
        self._durability_store = durability_store

    @staticmethod
    def _key(tenant_id: str, subject_ref: str, subject_role: LocalitySubjectRole) -> _Key:
        return (tenant_id, subject_ref, subject_role.value)

    def register(self, record: LocalityRecord) -> LocalityRecord:
        with self._lock:
            key = self._key(record.tenant_id, record.subject_ref, record.subject_role)
            self._current[key] = record
            self._history.setdefault(key, []).append(record)
            if self._durability_store is not None:
                self._durability_store.save_locality_record(record)
            return record

    def _register_reconstructed(self, record: LocalityRecord) -> None:
        """INTERNAL ONLY -- fresh-process rehydration of the current record from durable
        state (see akaalEngine.fabric.durability.reconstruct_locality_registry). Full
        history is not durably persisted, so reconstruction only restores the current
        pointer; the history list starts fresh in the new process."""
        with self._lock:
            key = self._key(record.tenant_id, record.subject_ref, record.subject_role)
            self._current[key] = record
            self._history.setdefault(key, []).append(record)

    def get_current(
        self, subject_ref: str, subject_role: LocalitySubjectRole, tenant_id: str
    ) -> LocalityRecord:
        with self._lock:
            key = self._key(tenant_id, subject_ref, subject_role)
            record = self._current.get(key)
            if record is None:
                raise UnknownLocalityError(
                    f"No LocalityRecord registered for subject_ref={subject_ref!r} "
                    f"role={subject_role.value!r} tenant_id={tenant_id!r}."
                )
            return record

    def try_get_current(
        self, subject_ref: str, subject_role: LocalitySubjectRole, tenant_id: str
    ) -> Optional[LocalityRecord]:
        with self._lock:
            return self._current.get(self._key(tenant_id, subject_ref, subject_role))

    def mark_stale(
        self, subject_ref: str, subject_role: LocalitySubjectRole, tenant_id: str
    ) -> LocalityRecord:
        """Explicit staleness transition -- a caller (e.g. a periodic re-observation
        sweep, or a topology-change handler) marks a record stale rather than deleting
        it, preserving the audit trail. Never auto-expires on a timer inside this class:
        staleness is always an explicit, caller-driven fact."""
        with self._lock:
            current = self.get_current(subject_ref, subject_role, tenant_id)
            if current.stale:
                return current
            updated = LocalityRecord(
                subject_ref=current.subject_ref,
                subject_role=current.subject_role,
                tenant_id=current.tenant_id,
                cloud_provider=current.cloud_provider,
                country=current.country,
                jurisdiction=current.jurisdiction,
                sovereignty_zone=current.sovereignty_zone,
                region=current.region,
                availability_zone=current.availability_zone,
                datacenter=current.datacenter,
                network=current.network,
                kubernetes_cluster=current.kubernetes_cluster,
                execution_site=current.execution_site,
                storage_location=current.storage_location,
                confidence=current.confidence,
                provenance_source=current.provenance_source,
                observed_at=current.observed_at,
                stale=True,
            )
            key = self._key(tenant_id, subject_ref, subject_role)
            self._current[key] = updated
            self._history.setdefault(key, []).append(updated)
            if self._durability_store is not None:
                self._durability_store.save_locality_record(updated)
            return updated

    def history(
        self, subject_ref: str, subject_role: LocalitySubjectRole, tenant_id: str
    ) -> Tuple[LocalityRecord, ...]:
        with self._lock:
            return tuple(self._history.get(self._key(tenant_id, subject_ref, subject_role), ()))

    def list_current_for_tenant(self, tenant_id: str) -> Tuple[LocalityRecord, ...]:
        with self._lock:
            return tuple(r for (t, _, _), r in self._current.items() if t == tenant_id)


default_locality_registry = LocalityRegistry()
