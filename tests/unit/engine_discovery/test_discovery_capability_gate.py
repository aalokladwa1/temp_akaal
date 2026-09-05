"""
tests/unit/engine_discovery/test_discovery_capability_gate.py
=================================================================
Hostile-review follow-up (BLOCKER #5, partial closure): negative-capability enforcement
via ResolvedStrategyHandle.require_capability() was only wired into CDC. This proves the
identical mechanism now works for Discovery too -- a provider that explicitly declares a
capability unsupported cannot be resolved for that capability through
DiscoverySessionCoordinator.resolve_discovery_strategy(required_capability=...), and the
change is backward-compatible (omitting required_capability preserves prior behavior,
confirmed by the full pre-existing discovery suite staying green).

Real ExtensionsAuthority, real DiscoverySessionCoordinator, real BaseDiscoveryStrategy
subclass -- no mocks for the assertion under test.
"""

from __future__ import annotations

import pytest

from akaalEngine.discovery.core.coordinator import DiscoverySessionCoordinator
from akaalEngine.discovery.errors.exceptions import UnsupportedDiscoveryFeatureError
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
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
from akaalEngine.extensions.resolution.resolver import StrategyResolver
from akaalEngine.extensions.spi.authority_contract import AuthorityContractDefinition


class _StubDiscoveryStrategy(BaseDiscoveryStrategy):
    """Minimal real BaseDiscoveryStrategy subclass -- only used to prove capability gating."""

    @property
    def provider_id(self) -> str:
        return "stub-provider"

    def discover_endpoint_identity(self, *a, **kw):
        return None

    def discover_namespaces(self, *a, **kw):
        return None

    def discover_objects_page(self, *a, **kw):
        return None

    def discover_object_structure(self, *a, **kw):
        return None

    def check_read_only_permissions(self, *a, **kw):
        return None

    def discover_permissions(self, *a, **kw):
        return None

    def discover_environment(self, *a, **kw):
        return None

    def discover_topology(self, *a, **kw):
        return None

    def discover_cdc_prerequisites(self, *a, **kw):
        return None

    def sample_data(self, *a, **kw):
        return None


def _fresh_coordinator_and_authority() -> DiscoverySessionCoordinator:
    fresh_registry = ExtensionRegistry()
    fresh_lifecycle_mgr = LifecycleManager()
    fresh_resolver = StrategyResolver(registry=fresh_registry, lifecycle_manager=fresh_lifecycle_mgr)
    ext_auth = ExtensionsAuthority(
        registry=fresh_registry,
        lifecycle_manager=fresh_lifecycle_mgr,
        strategy_resolver=fresh_resolver,
        auto_bootstrap=False,
    )
    ext_auth.register_authority_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("discovery"),
            contract_version="1.0.0",
            description="Discovery contract",
            expected_base_type=BaseDiscoveryStrategy,
        )
    )
    return DiscoverySessionCoordinator(extensions_authority=ext_auth), ext_auth


def _register_provider(ext_auth, ext_id: str, provider_id: str, schema_discovery_supported: bool):
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{provider_id}-strat"),
        authority_id=AuthorityId("discovery"),
        provider_id=ProviderId(provider_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_StubDiscoveryStrategy,
        capabilities=(
            CapabilityDeclaration(capability_name="SCHEMA_DISCOVERY", is_supported=schema_discovery_supported),
        ),
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


def test_discovery_resolves_normally_without_required_capability_backward_compat():
    coordinator, ext_auth = _fresh_coordinator_and_authority()
    _register_provider(ext_auth, "ext.a", "prov-a", schema_discovery_supported=True)
    strategy, handle = coordinator.resolve_discovery_strategy("prov-a")
    assert isinstance(strategy, _StubDiscoveryStrategy)
    handle.release()


def test_discovery_negative_capability_blocks_resolution_when_required():
    coordinator, ext_auth = _fresh_coordinator_and_authority()
    _register_provider(ext_auth, "ext.b", "prov-b", schema_discovery_supported=False)
    with pytest.raises(UnsupportedDiscoveryFeatureError):
        coordinator.resolve_discovery_strategy("prov-b", required_capability="SCHEMA_DISCOVERY")


def test_discovery_positive_capability_permits_resolution_when_required():
    coordinator, ext_auth = _fresh_coordinator_and_authority()
    _register_provider(ext_auth, "ext.c", "prov-c", schema_discovery_supported=True)
    strategy, handle = coordinator.resolve_discovery_strategy("prov-c", required_capability="SCHEMA_DISCOVERY")
    assert isinstance(strategy, _StubDiscoveryStrategy)
    handle.release()
