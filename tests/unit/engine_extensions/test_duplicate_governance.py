"""
tests.unit.engine_extensions.test_duplicate_governance
======================================================
Tests for ownership protection against hijacking, duplicate registration rejection, and explicit replacement governance.
"""

import pytest
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.models import (
    AuthorityId,
    CompatibilityRange,
    ExtensionId,
    ExtensionManifest,
    ExtensionOrigin,
    ProviderContribution,
    ProviderId,
    StrategyContribution,
    StrategyId,
)
from akaalEngine.extensions.errors.taxonomy import ExtensionConflictError
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)


def _create_simple_manifest(ext_id: str, prov_id: str, origin: ExtensionOrigin = ExtensionOrigin.THIRD_PARTY_PACKAGE) -> ExtensionManifest:
    default_contract_registry.register_contract(
        AuthorityContractDefinition(
            authority_id=AuthorityId("transport"),
            contract_version="1.0.0",
            description="Transport Contract",
        )
    )
    strat = StrategyContribution(
        strategy_id=StrategyId(f"{prov_id}-strat"),
        authority_id=AuthorityId("transport"),
        provider_id=ProviderId(prov_id),
        contract_version_range=CompatibilityRange("*"),
        strategy_factory=lambda: object(),
    )
    prov = ProviderContribution(
        provider_id=ProviderId(prov_id),
        vendor_name="Vendor",
        display_name="Provider",
        family="relational",
        strategies=(strat,),
    )
    return ExtensionManifest(
        extension_id=ExtensionId(ext_id),
        version="1.0.0",
        display_name=f"Extension {ext_id}",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        origin=origin,
        provider_contributions=(prov,),
    )


def test_duplicate_extension_rejection_by_default():
    reg = ExtensionRegistry()
    m1 = _create_simple_manifest("ext-a", "prov-a")
    reg.register_extension(m1)

    # Registering duplicate without allow_replace must fail
    m1_dup = _create_simple_manifest("ext-a", "prov-a")
    with pytest.raises(ExtensionConflictError) as exc_info:
        reg.register_extension(m1_dup, allow_replace=False)
    assert "already registered" in str(exc_info.value)

    # Registering with allow_replace succeeds
    reg.register_extension(m1_dup, allow_replace=True)
    assert reg.get_generation().value == 3


def test_hijack_protection_for_builtin_providers():
    reg = ExtensionRegistry()
    builtin_m = _create_simple_manifest("builtin-pg", "postgresql", origin=ExtensionOrigin.BUILTIN)
    reg.register_extension(builtin_m)

    # External extension trying to register 'postgresql' provider without replacement authorization fails
    third_party_m = _create_simple_manifest("rogue-pg-ext", "postgresql", origin=ExtensionOrigin.THIRD_PARTY_PACKAGE)
    with pytest.raises(ExtensionConflictError) as exc_info:
        reg.register_extension(third_party_m, allow_replace=False)
    assert "Cross-owner replacement or takeover" in str(exc_info.value)

    # External extension trying to replace 'postgresql' provider with allow_replace=True is rejected (cannot hijack built-in or any cross-owner)
    with pytest.raises(ExtensionConflictError) as exc_info2:
        reg.register_extension(third_party_m, allow_replace=True)
    assert "Cross-owner replacement or takeover" in str(exc_info2.value)
