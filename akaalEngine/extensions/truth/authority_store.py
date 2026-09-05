"""
akaalEngine.extensions.truth.authority_store
================================================
The authoritative record of AKAAL-issued certifications, distinct from
akaalEngine.extensions.models.proof.CertificationReference (which is merely a CLAIM
a manifest/strategy carries -- data until verified, never trust by itself).

Before this module existed, ProofResolver trusted any CertificationReference object
attached to a StrategyContribution directly: a strategy_factory could construct
CertificationReference(certified_level=LIVE_PROVEN, certifier_authority="AKAAL
Certification Program", ...) itself, and ProofResolver would honor it -- self-elevation,
with no authoritative AKAAL-controlled record involved at all. This module closes that:
a CertificationReference is now only honored if it resolves, by certification_id, to a
CertificationRecord that was explicitly registered here (by an AKAAL-controlled
certification process, never by extension code), AND every identity dimension
(extension_id, extension_version, provider_id, capability_name) matches exactly, AND
the record is neither expired nor revoked.

Lives in truth/ (not certification/) deliberately: proof_resolver.py and
capability_resolver.py are its only real consumers, and certification/__init__.py eagerly
imports runner.py -> authority.py -> resolution/ -> truth/, so placing this module under
certification/ instead would create a circular import (proven at implementation time).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from akaalEngine.extensions.models.enums import ProofLevel


@dataclass(frozen=True)
class CertificationRecord:
    """
    An authoritative AKAAL-issued certification. Only constructible by whoever holds a
    reference to a CertificationAuthorityStore and calls register_certification() --
    never derived from an untrusted manifest/strategy claim.
    """
    certification_id: str
    extension_id: str
    extension_version: str
    provider_id: str
    capability_name: str
    certifier_authority: str
    certified_level: ProofLevel
    issued_at: str
    expires_at: Optional[str] = None
    akaal_version_range: str = "*"
    provider_version_range: Optional[str] = None
    strategy_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.certification_id:
            raise ValueError("CertificationRecord.certification_id must not be empty.")
        object.__setattr__(self, "capability_name", self.capability_name.strip().upper())


class CertificationAuthorityStore:
    """
    Thread-safe registry of authoritative CertificationRecord entries and their
    revocation state. In-memory only -- durable persistence, if required, is the
    caller's composition-root responsibility (mirrors PublisherTrustStore's design).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, CertificationRecord] = {}
        self._revoked: set[str] = set()

    def register_certification(self, record: CertificationRecord) -> None:
        with self._lock:
            self._records[record.certification_id] = record

    def revoke_certification(self, certification_id: str) -> None:
        with self._lock:
            self._revoked.add(certification_id)

    def is_revoked(self, certification_id: str) -> bool:
        with self._lock:
            return certification_id in self._revoked

    def lookup(self, certification_id: str) -> Optional[CertificationRecord]:
        with self._lock:
            return self._records.get(certification_id)

    def resolve_authoritative_level(
        self,
        certification_id: str,
        extension_id: str,
        extension_version: str,
        provider_id: str,
        capability_name: str,
        strategy_id: Optional[str] = None,
        akaal_version: Optional[str] = None,
        provider_version: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Optional[ProofLevel]:
        """
        Returns the authoritative certified ProofLevel ONLY if every identity dimension
        matches exactly and the record is neither expired nor revoked. Returns None
        (never raises) for any mismatch -- a rejected claim degrades to whatever level
        can be established without it, it does not fail the whole resolution.
        """
        now = now or datetime.now(timezone.utc)
        record = self.lookup(certification_id)
        if record is None:
            return None
        if self.is_revoked(certification_id):
            return None
        if record.extension_id != extension_id:
            return None
        if record.extension_version != extension_version:
            return None
        if record.provider_id != provider_id:
            return None
        if record.capability_name != capability_name.strip().upper():
            return None

        # Exact strategy binding check
        if record.strategy_id is not None and strategy_id is not None:
            if record.strategy_id != strategy_id:
                return None
        elif record.strategy_id is not None and strategy_id is None:
            return None

        # Engine version range check
        if record.akaal_version_range and record.akaal_version_range != "*" and akaal_version is not None:
            from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
            try:
                res = CompatibilityEvaluator.evaluate("akaal_engine", akaal_version, record.akaal_version_range)
                if not res.is_compatible:
                    return None
            except Exception:
                return None

        # Provider version range check
        if record.provider_version_range and provider_version is not None:
            from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
            try:
                res = CompatibilityEvaluator.evaluate("provider", provider_version, record.provider_version_range)
                if not res.is_compatible:
                    return None
            except Exception:
                return None

        if record.expires_at is not None:
            try:
                expires = datetime.fromisoformat(record.expires_at)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if now > expires:
                    return None
            except ValueError:
                return None
        return record.certified_level


default_certification_authority_store = CertificationAuthorityStore()
