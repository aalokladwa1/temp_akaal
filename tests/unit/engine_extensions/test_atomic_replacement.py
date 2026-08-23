"""
tests.unit.engine_extensions.test_atomic_replacement
====================================================
Tests for transactional rollback on bridge mutation failure during extension replacement.
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
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.errors.taxonomy import ExtensionRegistrationError


from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)


def test_transactional_rollback_on_bridge_failure():
    default_contract_registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )
    reg = ExtensionRegistry()

    strat1 = StrategyContribution(
        strategy_id=StrategyId("s1"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("p1"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov1 = ProviderContribution(
        provider_id=ProviderId("p1"),
        vendor_name="V1",
        display_name="P1",
        family="relational",
        strategies=(strat1,),
    )
    m1 = ExtensionManifest(
        extension_id=ExtensionId("ext-1"),
        version="1.0.0",
        display_name="Ext 1",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov1,),
    )
    reg.register_extension(m1)
    assert reg.get_generation().value == 2

    # Attempt replacement with a multi-step bridge mutation where step 2 fails
    applied_mutations = []
    rolled_back_mutations = []

    def successful_bridge_mutation_1():
        applied_mutations.append(1)

    def rollback_bridge_mutation_1():
        rolled_back_mutations.append(1)

    def failing_bridge_mutation_2():
        raise RuntimeError("Simulated external bridge connection failure at step 2!")

    def rollback_bridge_mutation_2():
        rolled_back_mutations.append(2)

    m2 = ExtensionManifest(
        extension_id=ExtensionId("ext-1"),
        version="1.1.0",
        display_name="Ext 1 Updated",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov1,),
    )

    with pytest.raises(ExtensionRegistrationError) as exc_info:
        reg.register_extension(
            manifest=m2,
            allow_replace=True,
            bridge_mutations=(successful_bridge_mutation_1, failing_bridge_mutation_2),
            bridge_rollbacks=(rollback_bridge_mutation_1, rollback_bridge_mutation_2),
        )

    assert "Bridge mutation failed" in str(exc_info.value)
    # Rollback for step 1 was executed because step 1 was applied before step 2 failed
    assert applied_mutations == [1]
    assert rolled_back_mutations == [1]
    # Generation remains 2 and original version 1.0.0 remains active
    assert reg.get_generation().value == 2
    assert reg.get_snapshot().get_extension(ExtensionId("ext-1")).version == "1.0.0"
