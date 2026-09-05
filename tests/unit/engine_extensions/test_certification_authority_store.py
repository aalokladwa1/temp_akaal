"""
tests.unit.engine_extensions.test_certification_authority_store
====================================================================
Hostile-review blocker #9 (high severity): direct verification of
CertificationAuthorityStore.resolve_authoritative_level() against every named attack:
fake certification ID, another provider's certificate, another connector version,
provider-version mismatch, expired record, revoked record, and mismatched capability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.truth.authority_store import CertificationAuthorityStore, CertificationRecord

_NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _real_record(**overrides) -> CertificationRecord:
    defaults = dict(
        certification_id="cert-real-001",
        extension_id="ext.real",
        extension_version="2.0.0",
        provider_id="real-provider",
        capability_name="BULK_WRITE",
        certifier_authority="AKAAL Certification Program",
        certified_level=ProofLevel.LIVE_PROVEN,
        issued_at="2026-01-01T00:00:00+00:00",
    )
    defaults.update(overrides)
    return CertificationRecord(**defaults)


def test_genuine_record_resolves_authoritatively():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level == ProofLevel.LIVE_PROVEN


def test_fake_certification_id_resolves_to_none():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-does-not-exist", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None


def test_another_extensions_certification_id_reused_is_rejected():
    """A real certification_id exists, but for a DIFFERENT extension -- reuse must fail."""
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.attacker", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None


def test_another_providers_certificate_is_rejected():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="different-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None


def test_version_mismatch_is_rejected():
    """The certification was issued for version 2.0.0 -- claiming it for 3.0.0 must fail."""
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="3.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None


def test_capability_mismatch_is_rejected():
    """Certified for BULK_WRITE -- must not be usable to certify a different capability."""
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="CDC_CAPTURE", now=_NOW,
    )
    assert level is None


def test_expired_record_is_rejected():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record(expires_at="2026-01-31T00:00:00+00:00"))  # expired before _NOW
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None


def test_not_yet_expired_record_still_resolves():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record(expires_at="2027-01-01T00:00:00+00:00"))  # future
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level == ProofLevel.LIVE_PROVEN


def test_revoked_record_is_rejected_even_though_still_registered():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record())
    store.revoke_certification("cert-real-001")
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None
    # Confirmed still present in the store (not deleted) -- revocation is a distinct state.
    assert store.lookup("cert-real-001") is not None


def test_lookup_of_unregistered_id_returns_none_not_an_error():
    store = CertificationAuthorityStore()
    assert store.lookup("nonexistent") is None


def test_malformed_expiry_timestamp_fails_closed_not_open():
    store = CertificationAuthorityStore()
    store.register_certification(_real_record(expires_at="not-a-real-timestamp"))
    level = store.resolve_authoritative_level(
        certification_id="cert-real-001", extension_id="ext.real", extension_version="2.0.0",
        provider_id="real-provider", capability_name="BULK_WRITE", now=_NOW,
    )
    assert level is None
