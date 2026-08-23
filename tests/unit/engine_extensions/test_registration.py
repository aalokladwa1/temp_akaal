"""
tests.unit.engine_extensions.test_registration
==============================================
Tests for atomic extension registration, copy-on-write immutable snapshot publishing, and monotonic generation numbering.
"""

import pytest
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    RegistryGeneration,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.errors.taxonomy import IncompatibleEngineVersionError
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)


def test_atomic_registration_and_generation_bump():
    default_contract_registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )
    reg = ExtensionRegistry()
    initial_snap = reg.get_snapshot()
    assert initial_snap.generation.value == 1
    assert len(initial_snap.list_all_extensions()) == 0

    strat = StrategyContribution(
        strategy_id=StrategyId("s1"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("p1"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId("p1"),
        vendor_name="V1",
        display_name="P1",
        family="relational",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext-1"),
        version="1.0.0",
        display_name="Extension 1",
        engine_version_range=CompatibilityRange(">=1.0.0, <2.0.0"),
        provider_contributions=(prov,),
    )

    new_snap = reg.register_extension(manifest)
    assert new_snap.generation.value == 2
    assert reg.get_generation().value == 2
    assert len(new_snap.list_all_extensions()) == 1
    assert new_snap.get_extension(ExtensionId("ext-1")) == manifest
    assert new_snap.get_provider(ProviderId("p1")) == prov
    assert new_snap.get_strategy(StrategyId("s1")) == strat

    # Ensure prior snapshot is immutable and untouched
    assert initial_snap.generation.value == 1
    assert len(initial_snap.list_all_extensions()) == 0


def test_registration_incompatible_engine_version():
    reg = ExtensionRegistry()
    manifest = ExtensionManifest(
        extension_id=ExtensionId("future-ext"),
        version="1.0.0",
        display_name="Future Extension",
        engine_version_range=CompatibilityRange(">=2.0.0"),  # Incompatible with 1.0.0!
        provider_contributions=(),
    )

    with pytest.raises(IncompatibleEngineVersionError) as exc_info:
        reg.register_extension(manifest)
    assert "requires engine version" in str(exc_info.value)
    assert reg.get_generation().value == 1  # No generation bump on failure
