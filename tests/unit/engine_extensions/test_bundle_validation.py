"""
tests.unit.engine_extensions.test_bundle_validation
===================================================
Tests for provider bundles, multi-authority contributions, and manifest structural validation.
"""

import pytest
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ExtensionOrigin,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.spi.provider_bundle import ProviderBundle
from akaalEngine.extensions.spi.authority_contract import AuthorityContractRegistry
from akaalEngine.extensions.spi.validators import ManifestValidator
from akaalEngine.extensions.errors.taxonomy import ExtensionRegistrationError


def test_provider_bundle_creation_and_conversion():
    strat_conn = StrategyContribution(
        strategy_id=StrategyId("pg-conn"),
        authority_id=AuthorityId("connection"),
        provider_id=ProviderId("postgres_custom"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=lambda: object(),
        implementation_version="1.0.0",
    )
    strat_disc = StrategyContribution(
        strategy_id=StrategyId("pg-disc"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId("postgres_custom"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=lambda: object(),
        implementation_version="1.0.0",
    )

    bundle = ProviderBundle(
        provider_id=ProviderId("postgres_custom"),
        vendor_name="PostgreSQL Community",
        display_name="Custom PostgreSQL",
        family="relational",
        strategies=(strat_conn, strat_disc),
    )

    contrib = bundle.to_contribution()
    assert contrib.provider_id.value == "postgres_custom"
    assert len(contrib.strategies) == 2
    assert contrib.get_strategy_for_authority(AuthorityId("connection")) == strat_conn
    assert contrib.get_strategy_for_authority(AuthorityId("discovery")) == strat_disc
    assert contrib.get_strategy_for_authority(AuthorityId("schema")) is None


from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
)


def test_manifest_validation_success():
    contracts = AuthorityContractRegistry()
    contracts.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )

    strat = StrategyContribution(
        strategy_id=StrategyId("custom-strat"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("custom_prov"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId("custom_prov"),
        vendor_name="Vendor",
        display_name="Custom Provider",
        family="storage",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("valid-ext"),
        version="1.0.0",
        display_name="Valid Extension",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )

    ManifestValidator.validate_manifest(manifest, contracts)


def test_manifest_validation_mismatched_provider_id():
    contracts = AuthorityContractRegistry()
    contracts.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("connection"),
            contract_version="1.0.0",
            description="Connection Contract",
        )
    )

    strat = StrategyContribution(
        strategy_id=StrategyId("strat-1"),
        authority_id=AuthorityId("connection"),
        provider_id=ProviderId("prov_other"),  # Mismatch!
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId("prov_main"),
        vendor_name="Vendor",
        display_name="Provider Main",
        family="relational",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("invalid-ext"),
        version="1.0.0",
        display_name="Invalid Extension",
        engine_version_range=CompatibilityRange("*"),
        provider_contributions=(prov,),
    )

    with pytest.raises(ExtensionRegistrationError) as exc_info:
        ManifestValidator.validate_manifest(manifest, contracts)
    assert "does not match enclosing provider" in str(exc_info.value)
