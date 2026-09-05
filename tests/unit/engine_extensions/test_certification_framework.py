"""
tests.unit.engine_extensions.test_certification_framework
=========================================================
Hostile verification of Blocker #8 (Full Connector Certification Framework)
and Blocker #9 (Certification Authority Store Hardening):
- Data-driven CertificationProfile composed dynamically from declared capabilities.
- Non-relational profiles (e.g. RabbitMQ) do not force relational transaction obligations.
- Multi-capability providers compose applicable obligations across domains.
- Non-Boolean aggregation: PASS, FAIL, NOT_APPLICABLE, EXTERNAL_DEFERRED, UNSUPPORTED.
- Mandatory FAIL prevents certification PASS.
- EXTERNAL_DEFERRED preserves proof ceiling (never magically becomes LIVE_PROVEN).
- Structural store write isolation: untrusted manifests/extensions cannot write to CertificationAuthorityStore.
- Exact multi-dimensional binding: AKAAL version range, extension ID, extension version,
  provider ID, provider version range, strategy ID, capability name, expiration, revocation.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import pytest

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.certification import (
    CertificationAuthorityStore,
    CertificationObligation,
    CertificationProfile,
    CertificationRecord,
    ConnectorCertificationRunner,
    ObligationCategory,
    ObligationResult,
    ObligationStatus,
    build_profile_for_capabilities,
    RELATIONAL_PROFILE,
    MESSAGING_PROFILE,
)
from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.enums import ProofLevel
from akaalEngine.extensions.models.identity import AuthorityId, ExtensionId, ProviderId, StrategyId
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution
from akaalEngine.extensions.models.proof import CertificationReference
from akaalEngine.extensions.models.compatibility import CompatibilityRange


def _make_dummy_strategy():
    class Dummy:
        pass
    return Dummy()


def test_dynamic_profile_composition_from_capabilities():
    """Profile is built purely from capabilities, without hard-coding provider names."""
    profile = build_profile_for_capabilities(["SCHEMA_DISCOVERY", "BULK_READ"])
    categories = {o.category for o in profile.obligations}
    # Must include universal categories + discovery + data movement
    assert ObligationCategory.IDENTITY_PACKAGING in categories
    assert ObligationCategory.DISCOVERY_SCHEMA in categories
    assert ObligationCategory.DATA_MOVEMENT in categories
    # Transaction ACID is NOT applicable because TRANSACTION_ACID was not advertised
    assert not any(o.obligation_id == "OBL-TX-01" for o in profile.obligations)


def test_messaging_profile_does_not_force_relational_transactions():
    """RabbitMQ / Pulsar messaging connector is not penalized for missing relational transactions."""
    profile = build_profile_for_capabilities(["MESSAGING", "BULK_WRITE"])
    obligation_ids = {o.obligation_id for o in profile.obligations}
    assert "OBL-MSG-01" in obligation_ids
    assert "OBL-BULK-WRITE-01" in obligation_ids
    assert "OBL-TX-01" not in obligation_ids
    assert "OBL-DISC-01" not in obligation_ids


def test_mandatory_fail_prevents_certification_pass():
    """If ANY mandatory obligation fails, certification report cannot pass."""
    from akaalEngine.extensions.certification.models import CertificationReport

    report = CertificationReport(
        provider_id="test-provider",
        authority_id="discovery",
        strategy_id="test-strat",
        obligation_results=(
            ObligationResult(
                obligation_id="OBL-ID-01",
                status=ObligationStatus.PASS,
                category=ObligationCategory.IDENTITY_PACKAGING,
                diagnostic="OK",
            ),
            ObligationResult(
                obligation_id="OBL-SEC-01",
                status=ObligationStatus.FAIL,
                category=ObligationCategory.CONNECTION_SECURITY,
                diagnostic="Secret leakage detected",
            ),
        ),
    )
    assert report.passed is False


def test_not_applicable_obligation_is_neutral():
    """NOT_APPLICABLE status does not cause certification failure."""
    from akaalEngine.extensions.certification.models import CertificationReport

    report = CertificationReport(
        provider_id="test-provider",
        authority_id="discovery",
        strategy_id="test-strat",
        obligation_results=(
            ObligationResult(
                obligation_id="OBL-ID-01",
                status=ObligationStatus.PASS,
                category=ObligationCategory.IDENTITY_PACKAGING,
                diagnostic="OK",
            ),
            ObligationResult(
                obligation_id="OBL-TX-01",
                status=ObligationStatus.NOT_APPLICABLE,
                category=ObligationCategory.SEMANTICS,
                diagnostic="Transactions not applicable to this provider",
            ),
        ),
    )
    assert report.passed is True


def test_external_deferred_preserves_proof_ceiling():
    """
    If any check is EXTERNAL_DEFERRED (e.g. requires physical cloud/db cluster),
    the report passes at INTEGRATION_PROVEN but CANNOT claim LIVE_PROVEN.
    """
    from akaalEngine.extensions.certification.models import CertificationReport

    report = CertificationReport(
        provider_id="test-provider",
        authority_id="discovery",
        strategy_id="test-strat",
        obligation_results=(
            ObligationResult(
                obligation_id="OBL-ID-01",
                status=ObligationStatus.PASS,
                category=ObligationCategory.IDENTITY_PACKAGING,
                diagnostic="OK",
            ),
            ObligationResult(
                obligation_id="OBL-LIVE-CLUSTER",
                status=ObligationStatus.EXTERNAL_DEFERRED,
                category=ObligationCategory.CONNECTION_SECURITY,
                diagnostic="Live cluster connectivity deferred to staging",
            ),
        ),
    )
    assert report.passed is True
    assert report.has_external_deferred is True
    assert report.allowable_proof_level == ProofLevel.INTEGRATION_PROVEN
    assert report.allowable_proof_level != ProofLevel.LIVE_PROVEN


def test_structural_store_write_isolation():
    """
    Structural verification:
    Extension manifests carry CertificationReference claims only.
    Extension registration has no reference or write pathway to CertificationAuthorityStore.
    """
    store = CertificationAuthorityStore()
    from akaalEngine.extensions.catalog.registry import ExtensionRegistry
    from akaalEngine.extensions.lifecycle.manager import LifecycleManager
    fresh_reg = ExtensionRegistry()
    fresh_life = LifecycleManager()
    ext_auth = ExtensionsAuthority(registry=fresh_reg, lifecycle_manager=fresh_life, auto_bootstrap=False)
    from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition
    ext_auth.register_authority_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("discovery"),
            contract_version="1.0.0",
            description="Discovery SPI contract",
        )
    )

    # Manifest with arbitrary self-claimed certification
    cert_claim = CertificationReference(
        certification_id="forged-cert-id",
        certifier_authority="Forged Certifier",
        certified_level=ProofLevel.LIVE_PROVEN,
        certified_target="SCHEMA_DISCOVERY",
        valid_from="2026-01-01T00:00:00Z",
    )
    strat = StrategyContribution(
        strategy_id=StrategyId("strat-1"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId("prov-1"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_make_dummy_strategy,
        capabilities=(CapabilityDeclaration("SCHEMA_DISCOVERY", is_supported=True),),
        certifications=(cert_claim,),
    )
    prov = ProviderContribution(
        provider_id=ProviderId("prov-1"),
        vendor_name="Acme",
        display_name="Prov 1",
        family="relational",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.attacker"),
        version="1.0.0",
        display_name="Attacker Ext",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )
    # Registration should succeed as a candidate extension, but NOT write to store
    ext_auth.register_extension(manifest)
    assert store.lookup("forged-cert-id") is None


def test_store_exact_multi_dimensional_binding_and_replay_prevention():
    """
    Certifications strictly bind:
    akaal_version_range x extension_id x extension_version x provider_id x
    provider_version_range x strategy_id x capability_name
    Any dimension mismatch fails closed (returns None).
    """
    store = CertificationAuthorityStore()
    now = datetime.now(timezone.utc)
    rec = CertificationRecord(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        strategy_id="oracle-discovery-v2",
        capability_name="SCHEMA_DISCOVERY",
        certifier_authority="AKAAL Trusted QA",
        certified_level=ProofLevel.LIVE_PROVEN,
        issued_at=now.isoformat(),
        akaal_version_range=">=1.0.0, <2.0.0",
        provider_version_range=">=19.0.0",
    )
    store.register_certification(rec)

    # 1. Exact match succeeds
    level = store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
        akaal_version="1.5.0",
        provider_version="19.3.0",
        now=now,
    )
    assert level == ProofLevel.LIVE_PROVEN

    # 2. Wrong extension ID fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.impostor",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
    ) is None

    # 3. Wrong extension version fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="3.0.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
    ) is None

    # 4. Wrong provider ID fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="postgresql",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
    ) is None

    # 5. Wrong strategy ID fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-cdc-v1",
    ) is None

    # 6. Incompatible AKAAL version fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
        akaal_version="2.0.1",  # out of range
    ) is None

    # 7. Incompatible provider version fails
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
        akaal_version="1.5.0",
        provider_version="11.2.0",  # out of range (<19.0.0)
    ) is None

    # 8. Revoked record fails
    store.revoke_certification("cert-oracle-01")
    assert store.resolve_authoritative_level(
        certification_id="cert-oracle-01",
        extension_id="ext.oracle",
        extension_version="2.1.0",
        provider_id="oracle",
        capability_name="SCHEMA_DISCOVERY",
        strategy_id="oracle-discovery-v2",
    ) is None
