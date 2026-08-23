"""
tests.unit.engine_extensions.test_authority_contracts
=====================================================
Tests for authority contract definitions, registration, custom validation callables, and contract mismatch errors.
"""

from abc import ABC, abstractmethod
import pytest
from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    AuthorityContractRegistry,
)
from akaalEngine.extensions.errors.taxonomy import AuthorityContractMismatchError
from akaalEngine.extensions.spi.validators import ManifestValidator


class MockDiscoveryStrategyBase(ABC):
    @abstractmethod
    def discover_tables(self) -> list:
        raise NotImplementedError


class ValidDiscoveryStrategy(MockDiscoveryStrategyBase):
    def discover_tables(self) -> list:
        return ["table1", "table2"]


class InvalidDiscoveryStrategy:
    pass  # Does not inherit from MockDiscoveryStrategyBase


def test_contract_registration_and_validation():
    registry = AuthorityContractRegistry()
    
    contract = AuthorityContractDefinition(
        authority_id=AuthorityId("discovery"),
        contract_version="1.0.0",
        description="Discovery Authority Contract",
        expected_base_type=MockDiscoveryStrategyBase,
        known_capabilities=("SCHEMA_DISCOVERY", "TABLE_STATISTICS"),
    )
    registry.register_contract(contract)

    assert registry.has_contract(AuthorityId("discovery"))
    assert not registry.has_contract(AuthorityId("transport"))
    assert registry.get_contract(AuthorityId("discovery")) == contract

    # Validate strategy instance directly
    valid_inst = ValidDiscoveryStrategy()
    assert contract.validate_strategy_instance(valid_inst) is True

    invalid_inst = InvalidDiscoveryStrategy()
    with pytest.raises(AuthorityContractMismatchError) as exc_info:
        contract.validate_strategy_instance(invalid_inst)
    assert "does not inherit from expected base" in str(exc_info.value)


def test_manifest_validation_catches_contract_mismatch():
    registry = AuthorityContractRegistry()
    registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("discovery"),
            contract_version="1.0.0",
            description="Discovery Authority Contract",
            expected_base_type=MockDiscoveryStrategyBase,
        )
    )

    # 1. Unknown authority rejected
    strat_unknown_auth = StrategyContribution(
        strategy_id=StrategyId("strat-unknown"),
        authority_id=AuthorityId("unknown_authority"),
        provider_id=ProviderId("test_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=ValidDiscoveryStrategy,
    )
    prov1 = ProviderContribution(
        provider_id=ProviderId("test_db"),
        vendor_name="Vendor",
        display_name="Test DB",
        family="relational",
        strategies=(strat_unknown_auth,),
    )
    m_unknown = ExtensionManifest(
        extension_id=ExtensionId("unknown-auth-ext"),
        version="1.0.0",
        display_name="Unknown Auth Ext",
        engine_version_range=CompatibilityRange("*"),
        provider_contributions=(prov1,),
    )
    with pytest.raises(AuthorityContractMismatchError) as exc_info:
        ManifestValidator.validate_manifest(m_unknown, registry)
    assert "Unknown authority 'unknown_authority'" in str(exc_info.value)

    # 2. Incompatible contract version range rejected
    strat_incompat = StrategyContribution(
        strategy_id=StrategyId("strat-incompat"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId("test_db"),
        contract_version_range=CompatibilityRange(">=2.0.0"),  # Incompatible with contract 1.0.0
        strategy_factory=ValidDiscoveryStrategy,
    )
    prov2 = ProviderContribution(
        provider_id=ProviderId("test_db"),
        vendor_name="Vendor",
        display_name="Test DB",
        family="relational",
        strategies=(strat_incompat,),
    )
    m_incompat = ExtensionManifest(
        extension_id=ExtensionId("incompat-ext"),
        version="1.0.0",
        display_name="Incompat Ext",
        engine_version_range=CompatibilityRange("*"),
        provider_contributions=(prov2,),
    )
    with pytest.raises(AuthorityContractMismatchError) as exc_info2:
        ManifestValidator.validate_manifest(m_incompat, registry)
    assert "requires authority contract range" in str(exc_info2.value)

    # 3. Class type mismatch rejected
    strat_bad_class = StrategyContribution(
        strategy_id=StrategyId("strat-bad-class"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId("test_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=InvalidDiscoveryStrategy,  # Does not subclass MockDiscoveryStrategyBase
    )
    prov3 = ProviderContribution(
        provider_id=ProviderId("test_db"),
        vendor_name="Vendor",
        display_name="Test DB",
        family="relational",
        strategies=(strat_bad_class,),
    )
    m_bad_class = ExtensionManifest(
        extension_id=ExtensionId("bad-class-ext"),
        version="1.0.0",
        display_name="Bad Class Ext",
        engine_version_range=CompatibilityRange("*"),
        provider_contributions=(prov3,),
    )
    with pytest.raises(AuthorityContractMismatchError) as exc_info3:
        ManifestValidator.validate_manifest(m_bad_class, registry)
    assert "does not subclass MockDiscoveryStrategyBase" in str(exc_info3.value)


def test_lazy_factory_not_executed_during_registration():
    registry = AuthorityContractRegistry()
    registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("discovery"),
            contract_version="1.0.0",
            description="Discovery Authority Contract",
            expected_base_type=MockDiscoveryStrategyBase,
        )
    )

    factory_executed = False

    def heavy_factory():
        nonlocal factory_executed
        factory_executed = True
        return ValidDiscoveryStrategy()

    strat = StrategyContribution(
        strategy_id=StrategyId("lazy-strat"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId("test_db"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=heavy_factory,
    )
    prov = ProviderContribution(
        provider_id=ProviderId("test_db"),
        vendor_name="Vendor",
        display_name="Test DB",
        family="relational",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("lazy-ext"),
        version="1.0.0",
        display_name="Lazy Ext",
        engine_version_range=CompatibilityRange("*"),
        provider_contributions=(prov,),
    )

    ManifestValidator.validate_manifest(manifest, registry)
    # Factory was NOT executed during registration validation!
    assert factory_executed is False
