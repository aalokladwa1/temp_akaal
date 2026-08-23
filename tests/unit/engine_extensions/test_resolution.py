"""
tests.unit.engine_extensions.test_resolution
============================================
Tests for deterministic strategy resolution, capability filtering, priority selection, and ambiguity rejection.
"""

import pytest
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.lifecycle.manager import LifecycleManager
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ExtensionId,
    ExtensionLifecycleState,
    ExtensionManifest,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.resolution.resolver import StrategyResolver
from akaalEngine.extensions.errors.taxonomy import (
    AmbiguousStrategyError,
    LifecycleTransitionError,
    ProviderNotFoundError,
    StrategyNotFoundError,
)


class DummyTransportStrategy:
    def __init__(self, name: str):
        self.name = name


def test_strategy_resolution_by_capability_and_priority():
    reg = ExtensionRegistry()
    lm = LifecycleManager()
    resolver = StrategyResolver(registry=reg, lifecycle_manager=lm)

    s1 = StrategyContribution(
        strategy_id=StrategyId("s1-basic"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("my_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: DummyTransportStrategy("basic"),
        capabilities=(CapabilityDeclaration("BULK_READ", is_supported=True),),
        priority=50,
    )
    s2 = StrategyContribution(
        strategy_id=StrategyId("s2-fast"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("my_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: DummyTransportStrategy("fast"),
        capabilities=(
            CapabilityDeclaration("BULK_READ", is_supported=True),
            CapabilityDeclaration("PARALLEL_SLICING", is_supported=True),
        ),
        priority=100,
    )
    prov = ProviderContribution(
        provider_id=ProviderId("my_db"),
        vendor_name="Vendor",
        display_name="My DB",
        family="relational",
        strategies=(s1, s2),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext-transport"),
        version="1.0.0",
        display_name="Transport Ext",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )
    reg.register_extension(manifest)
    lm.transition_state(ExtensionId("ext-transport"), ExtensionLifecycleState.REGISTERED, reg.get_generation(), "Init")
    lm.transition_state(ExtensionId("ext-transport"), ExtensionLifecycleState.ACTIVE, reg.get_generation(), "Activate")

    # 1. Resolve without specific capabilities -> highest priority s2-fast chosen
    h1 = resolver.resolve_strategy("my_db", "transport")
    assert h1.strategy_id.value == "s2-fast"
    assert h1.strategy_instance.name == "fast"
    h1.release()

    # 2. Resolve requiring PARALLEL_SLICING -> s2-fast chosen
    h2 = resolver.resolve_strategy("my_db", "transport", required_capabilities=["PARALLEL_SLICING"])
    assert h2.strategy_id.value == "s2-fast"
    h2.release()

    # 3. Resolve requiring unsupported capability -> StrategyNotFoundError
    with pytest.raises(StrategyNotFoundError):
        resolver.resolve_strategy("my_db", "transport", required_capabilities=["NON_EXISTENT_CAP"])


def test_ambiguity_rejection():
    reg = ExtensionRegistry()
    lm = LifecycleManager()
    resolver = StrategyResolver(registry=reg, lifecycle_manager=lm)

    s1 = StrategyContribution(
        strategy_id=StrategyId("competing-1"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("my_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: DummyTransportStrategy("1"),
        priority=100,
    )
    s2 = StrategyContribution(
        strategy_id=StrategyId("competing-2"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId("my_db"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: DummyTransportStrategy("2"),
        priority=100,  # Same priority!
    )
    prov = ProviderContribution(
        provider_id=ProviderId("my_db"),
        vendor_name="Vendor",
        display_name="My DB",
        family="relational",
        strategies=(s1, s2),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ambiguous-ext"),
        version="1.0.0",
        display_name="Ambiguous Ext",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )
    reg.register_extension(manifest)
    lm.transition_state(ExtensionId("ambiguous-ext"), ExtensionLifecycleState.REGISTERED, reg.get_generation(), "Init")
    lm.transition_state(ExtensionId("ambiguous-ext"), ExtensionLifecycleState.ACTIVE, reg.get_generation(), "Activate")

    with pytest.raises(AmbiguousStrategyError) as exc_info:
        resolver.resolve_strategy("my_db", "transport")
    assert "multiple active strategies share priority" in str(exc_info.value)
