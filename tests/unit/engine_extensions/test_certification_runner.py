"""
tests.unit.engine_extensions.test_certification_runner
==========================================================
Hostile verification of P7A.5 connector certification: contract conformance,
capability-declaration integrity, and -- mandatorily -- that negative capability
declarations are genuinely enforced, not merely tracked as unread metadata.
"""

from __future__ import annotations

import pytest

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.certification.runner import ConnectorCertificationRunner
from akaalEngine.extensions.lifecycle.manager import LifecycleManager
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.resolution.resolver import StrategyResolver
from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition
from akaalEngine.extensions.truth.authority_store import CertificationAuthorityStore, CertificationRecord


class _ConformingStrategy:
    """A trivial but real implementation used as the SPI instance under certification."""
    def do_thing(self):
        return "ok"


class _NonConformingStrategy:
    pass


def _fresh_authority(cert_store: "CertificationAuthorityStore | None" = None) -> ExtensionsAuthority:
    fresh_registry = ExtensionRegistry()
    fresh_lifecycle_mgr = LifecycleManager()
    # Always an isolated store (never the process-global default) unless the caller
    # explicitly wants to test against a specific one -- avoids cross-test pollution of
    # the kind that previously broke the "28 providers" test via a shared registry.
    fresh_resolver = StrategyResolver(
        registry=fresh_registry,
        lifecycle_manager=fresh_lifecycle_mgr,
        certification_authority_store=cert_store or CertificationAuthorityStore(),
    )
    ext_auth = ExtensionsAuthority(
        registry=fresh_registry,
        lifecycle_manager=fresh_lifecycle_mgr,
        strategy_resolver=fresh_resolver,
        auto_bootstrap=False,
    )
    ext_auth.register_authority_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("test-authority"),
            contract_version="1.0.0",
            description="Test authority contract",
            expected_base_type=_ConformingStrategy,
        )
    )
    return ext_auth


def _register(ext_auth: ExtensionsAuthority, ext_id: str, provider_id: str, strategy_factory, capabilities, certifications=()):
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{provider_id}-strat"),
        authority_id=AuthorityId("test-authority"),
        provider_id=ProviderId(provider_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=strategy_factory,
        capabilities=capabilities,
        certifications=certifications,
    )
    prov = ProviderContribution(
        provider_id=ProviderId(provider_id), vendor_name="V", display_name="P",
        family="relational", strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId(ext_id), version="1.0.0", display_name=f"Ext {ext_id}",
        engine_version_range=CompatibilityRange(">=1.0.0"), provider_contributions=(prov,),
    )
    ext_auth.register_extension(manifest)
    ext_auth.activate_extension(ext_id)


def test_conforming_strategy_with_honest_negative_capability_certifies_clean():
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.good", "good-provider", _ConformingStrategy,
        capabilities=(
            CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),
            CapabilityDeclaration(capability_name="CDC_CAPTURE", is_supported=False),
        ),
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "good-provider", "test-authority")
    assert report.passed is True
    categories = {r.category for r in report.results}
    assert "IDENTITY_MANIFEST" in categories
    assert "CAPABILITY_TRUTH" in categories
    assert "NEGATIVE_CAPABILITY" in categories
    neg_results = [r for r in report.results if r.category == "NEGATIVE_CAPABILITY"]
    assert len(neg_results) == 1
    assert neg_results[0].capability_name == "CDC_CAPTURE"
    assert neg_results[0].passed is True


def test_non_conforming_strategy_instance_fails_contract_check():
    """
    Registration-time ManifestValidator already rejects a non-conforming CLASS factory
    (issubclass check). To exercise the certification runner's own runtime instance check,
    use a callable factory -- registration deliberately skips instance checks for those
    (documented in spi/validators.py as "lazy factory" behavior, since instantiating during
    registration would defeat lazy-loading) -- so this proves the runner's check is not
    simply redundant with registration-time validation, it closes that exact gap.
    """
    ext_auth = _fresh_authority()
    _register(ext_auth, "ext.bad", "bad-provider", lambda: _NonConformingStrategy(), capabilities=())
    report = ConnectorCertificationRunner.certify(ext_auth, "bad-provider", "test-authority")
    assert report.passed is False
    contract_results = [r for r in report.results if r.check_name == "contract_conformance"]
    assert len(contract_results) == 1
    assert contract_results[0].passed is False


def test_certification_report_with_zero_checks_never_reports_as_passed():
    from akaalEngine.extensions.certification.models import CertificationReport
    empty = CertificationReport(provider_id="p", authority_id="a", strategy_id="s", results=())
    assert empty.passed is False


def test_certification_fails_uncertified_authority_id():
    ext_auth = _fresh_authority()
    # Register a strategy for an authority that has NO registered contract
    strat = StrategyContribution(
        strategy_id=StrategyId("orphan-strat"),
        authority_id=AuthorityId("never-registered-authority"),
        provider_id=ProviderId("orphan-provider"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_ConformingStrategy,
    )
    # Registration itself must fail closed (unknown authority) -- confirms certification
    # can never even be reached for a strategy targeting an unregistered authority.
    from akaalEngine.extensions.errors.taxonomy import AuthorityContractMismatchError
    prov = ProviderContribution(
        provider_id=ProviderId("orphan-provider"), vendor_name="V", display_name="P",
        family="relational", strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.orphan"), version="1.0.0", display_name="Orphan",
        engine_version_range=CompatibilityRange(">=1.0.0"), provider_contributions=(prov,),
    )
    with pytest.raises(AuthorityContractMismatchError):
        ext_auth.register_extension(manifest)


def test_certification_does_not_fabricate_live_proven_without_real_certification_reference():
    """A capability with no ProofReference/CertificationReference cannot be certified LIVE_PROVEN."""
    ext_auth = _fresh_authority()
    _register(
        ext_auth, "ext.selfcert", "selfcert-provider", _ConformingStrategy,
        capabilities=(CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),),
        certifications=(),  # no real certification attached
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "selfcert-provider", "test-authority")
    cap_results = [r for r in report.results if r.capability_name == "BULK_READ"]
    assert len(cap_results) == 1
    assert "IMPLEMENTED" in cap_results[0].diagnostic or "DECLARED" in cap_results[0].diagnostic
    assert "LIVE_PROVEN" not in cap_results[0].diagnostic


def test_self_declared_certification_claim_does_not_elevate_without_authoritative_record():
    """
    Hostile-review blocker #9: the exact self-elevation exploit -- a strategy_factory
    attaches its own CertificationReference(certified_level=LIVE_PROVEN,
    certifier_authority="AKAAL Certification Program") with NO corresponding record ever
    registered in any CertificationAuthorityStore. This must NOT elevate the proof level;
    a bare claim is data, not proof.
    """
    self_declared_cert = CertificationReference(
        certification_id="cert-attacker-forged",
        certifier_authority="AKAAL Certification Program",  # claimed, not verified
        certified_level=ProofLevel.LIVE_PROVEN,
        certified_target="BULK_READ",
        valid_from="2026-01-01",
    )
    ext_auth = _fresh_authority()  # fresh, empty CertificationAuthorityStore -- nothing registered
    _register(
        ext_auth, "ext.forged_cert", "forged-cert-provider", _ConformingStrategy,
        capabilities=(CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),),
        certifications=(self_declared_cert,),
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "forged-cert-provider", "test-authority")
    cap_results = [r for r in report.results if r.capability_name == "BULK_READ"]
    assert len(cap_results) == 1
    assert "LIVE_PROVEN" not in cap_results[0].diagnostic, (
        "Self-declared CertificationReference elevated proof level without an authoritative "
        "record -- the exact self-elevation vulnerability this fix must close."
    )


def test_certification_reflects_real_certification_reference_when_genuinely_attached():
    """The positive case: LIVE_PROVEN IS reached, but only via a genuinely registered,
    identity-matched, non-expired, non-revoked CertificationRecord in the authority store."""
    store = CertificationAuthorityStore()
    store.register_certification(
        CertificationRecord(
            certification_id="cert-001",
            extension_id="ext.certified",
            extension_version="1.0.0",
            provider_id="certified-provider",
            capability_name="BULK_READ",
            certifier_authority="AKAAL Certification Program",
            certified_level=ProofLevel.LIVE_PROVEN,
            issued_at="2026-01-01T00:00:00+00:00",
        )
    )
    ext_auth = _fresh_authority(cert_store=store)
    real_cert = CertificationReference(
        certification_id="cert-001",
        certifier_authority="AKAAL Certification Program",
        certified_level=ProofLevel.LIVE_PROVEN,
        certified_target="BULK_READ",
        valid_from="2026-01-01",
    )
    _register(
        ext_auth, "ext.certified", "certified-provider", _ConformingStrategy,
        capabilities=(CapabilityDeclaration(capability_name="BULK_READ", is_supported=True),),
        certifications=(real_cert,),
    )
    report = ConnectorCertificationRunner.certify(ext_auth, "certified-provider", "test-authority")
    cap_results = [r for r in report.results if r.capability_name == "BULK_READ"]
    assert len(cap_results) == 1
    assert "LIVE_PROVEN" in cap_results[0].diagnostic
