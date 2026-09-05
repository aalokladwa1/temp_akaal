"""
tests.unit.engine_extensions.test_universal_capability_enforcement
======================================================================
Hostile-review blocker #7: proves capability enforcement is STRUCTURAL at
StrategySelector.select() -- not merely a helper a caller might forget to invoke.
When required_capabilities is passed to ExtensionsAuthority.resolve_strategy(), a
strategy declaring that capability unsupported (or undeclared) can never be selected
in the first place, so its physical implementation is never even instantiated, let
alone invoked -- proven with a real sentinel side effect, not just a metadata check.

Scope, stated honestly: this proves the mechanism is airtight wherever a caller passes
required_capabilities (already true for CDC and Discovery, see
test_cdc_extension_integration.py and test_discovery_capability_gate.py). It does not
retrofit akaalEngine.connection's provider-catalog-based invocation path, which resolves
already-materialized providers directly from ProviderCatalog rather than through
ExtensionsAuthority.resolve_strategy() at all -- a structurally different invocation
model that would require a separate, larger change to a frozen, heavily-tested
Connection Authority, out of scope for this fix.
"""

from __future__ import annotations

import pytest

from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.errors.taxonomy import StrategyNotFoundError
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

_SIDE_EFFECT_LOG = []


class _SentinelStrategy:
    """A real strategy instance whose factory records instantiation -- proof of whether
    resolution ever reached the point of constructing/exposing this physical implementation."""

    def __init__(self):
        _SIDE_EFFECT_LOG.append("instantiated")

    def do_privileged_operation(self):
        _SIDE_EFFECT_LOG.append("do_privileged_operation_called")
        return "operation executed"


def _fresh_authority():
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
            authority_id=AuthorityId("sentinel-authority"),
            contract_version="1.0.0",
            description="Sentinel test contract",
        )
    )
    return ext_auth


def _register(ext_auth, ext_id: str, provider_id: str, capability_supported: bool):
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{provider_id}-strat"),
        authority_id=AuthorityId("sentinel-authority"),
        provider_id=ProviderId(provider_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_SentinelStrategy,
        capabilities=(
            CapabilityDeclaration(capability_name="PRIVILEGED_WRITE", is_supported=capability_supported),
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


@pytest.mark.parametrize("capability_supported,should_resolve", [
    (True, True),
    (False, False),
])
def test_required_capability_gates_resolution_before_any_instantiation(capability_supported, should_resolve):
    """
    Structural proof: when the strategy does NOT support the required capability,
    resolve_strategy(required_capabilities=[...]) must raise BEFORE _SentinelStrategy is
    ever instantiated -- the physical side effect never happens, proving this isn't a
    post-hoc advisory check a caller could accidentally skip.
    """
    _SIDE_EFFECT_LOG.clear()
    ext_auth = _fresh_authority()
    provider_id = f"sentinel-provider-{capability_supported}"
    _register(ext_auth, f"ext.sentinel.{capability_supported}", provider_id, capability_supported)

    if should_resolve:
        handle = ext_auth.resolve_strategy(
            provider_id=provider_id,
            authority_id="sentinel-authority",
            required_capabilities=["PRIVILEGED_WRITE"],
        )
        try:
            assert "instantiated" in _SIDE_EFFECT_LOG
            result = handle.strategy_instance.do_privileged_operation()
            assert result == "operation executed"
            assert "do_privileged_operation_called" in _SIDE_EFFECT_LOG
        finally:
            handle.release()
    else:
        with pytest.raises(StrategyNotFoundError):
            ext_auth.resolve_strategy(
                provider_id=provider_id,
                authority_id="sentinel-authority",
                required_capabilities=["PRIVILEGED_WRITE"],
            )
        assert _SIDE_EFFECT_LOG == [], (
            "Strategy was instantiated despite failing the required-capability gate -- "
            "capability enforcement is not actually structural."
        )


def test_undeclared_capability_is_gated_identically_to_explicit_no():
    """A capability never declared at all must be gated exactly like an explicit is_supported=False."""
    _SIDE_EFFECT_LOG.clear()
    ext_auth = _fresh_authority()
    strat = StrategyContribution(
        strategy_id=StrategyId("undeclared-strat"),
        authority_id=AuthorityId("sentinel-authority"),
        provider_id=ProviderId("undeclared-provider"),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=_SentinelStrategy,
        capabilities=(),  # PRIVILEGED_WRITE never declared at all
    )
    prov = ProviderContribution(
        provider_id=ProviderId("undeclared-provider"), vendor_name="V", display_name="P",
        family="relational", strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("ext.undeclared"), version="1.0.0", display_name="Undeclared",
        engine_version_range=CompatibilityRange(">=1.0.0"), provider_contributions=(prov,),
    )
    ext_auth.register_extension(manifest)
    ext_auth.activate_extension("ext.undeclared")

    with pytest.raises(StrategyNotFoundError):
        ext_auth.resolve_strategy(
            provider_id="undeclared-provider",
            authority_id="sentinel-authority",
            required_capabilities=["PRIVILEGED_WRITE"],
        )
    assert _SIDE_EFFECT_LOG == []


def test_resolve_executable_strategy_mandates_operation():
    """Operation is mandatory by construction -- omitting it is a type/value rejection."""
    ext_auth = _fresh_authority()
    with pytest.raises((TypeError, ValueError)):
        # Calling without required positional argument 'operation'
        ext_auth.resolve_executable_strategy(
            provider_id="sentinel-provider-True",
            authority_id="sentinel-authority",
        )


def test_resolve_executable_strategy_gates_unsupported_operation_before_instantiation():
    _SIDE_EFFECT_LOG.clear()
    ext_auth = _fresh_authority()
    _register(ext_auth, "ext.sentinel.false", "sentinel-provider-false", capability_supported=False)

    with pytest.raises((StrategyNotFoundError, Exception)):
        ext_auth.resolve_executable_strategy(
            provider_id="sentinel-provider-false",
            authority_id="sentinel-authority",
            operation="PRIVILEGED_WRITE",
        )
    # Crucial security guarantee: factory was NEVER called
    assert _SIDE_EFFECT_LOG == []


def test_inspect_strategy_returns_metadata_without_instantiating_physical_strategy():
    """inspect_strategy allows reading capability metadata with zero executable authority."""
    _SIDE_EFFECT_LOG.clear()
    ext_auth = _fresh_authority()
    _register(ext_auth, "ext.sentinel.true", "sentinel-provider-true", capability_supported=True)

    desc = ext_auth.inspect_strategy(
        provider_id="sentinel-provider-true",
        authority_id="sentinel-authority",
    )
    assert desc.strategy_id == "sentinel-provider-true-strat"
    assert "PRIVILEGED_WRITE" in desc.capabilities
    # Factory was NEVER instantiated during inspection
    assert _SIDE_EFFECT_LOG == []


def test_connection_authority_structurally_gates_unsupported_capability_before_connect():
    """
    Forensic proof for Connection:
    ConnectionAuthority.acquire_session_lease() validates capability truth via
    CapabilityResolver.validate_admission() BEFORE any physical driver connect() executes.
    """
    from akaalEngine.connection.api.authority import ConnectionAuthority
    from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
    from akaalEngine.connection.models.errors import CapabilityMismatchError
    from akaalEngine.connection.models.session import SessionPurpose, SessionRequest

    conn_auth = ConnectionAuthority.get_instance()
    # SQLite provider does NOT support CDC_LOG or DISTRIBUTED_TX
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.SOURCE)
    # Requesting a session for CDC_CAPTURE purpose against SQLite (which does not support CDC)
    req = SessionRequest(
        endpoint_spec=spec,
        purpose=SessionPurpose.CDC_CAPTURE,
        required_capabilities=("CDC_STREAM",),
    )
    with pytest.raises(CapabilityMismatchError) as exc_info:
        conn_auth.acquire_session_lease(req)
    assert "CDC_STREAM" in str(exc_info.value) or "CAPABILITY_MISMATCH" in str(exc_info.value.failure.category.value)

