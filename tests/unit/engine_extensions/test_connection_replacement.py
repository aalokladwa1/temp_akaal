"""
tests.unit.engine_extensions.test_connection_replacement
========================================================
Tests verifying replacement of a Connection provider strategy through Extensions bridge and generation synchronization.
"""

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.extensions.authority import ExtensionsAuthority
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
    TrustTier,
)
from akaalEngine.extensions.spi.strategy_factory import InstanceStrategyFactory


class CustomEnhancedSQLiteStrategy(SQLiteProviderStrategy):
    PROVIDER_VERSION = "1.1.0"


def test_connection_strategy_replacement_through_extensions():
    ext_auth = ExtensionsAuthority.get_instance()
    conn_cat = default_provider_catalog

    initial_conn_gen = conn_cat.get_catalog_generation()
    initial_ext_gen = ext_auth.get_registry_generation()

    custom_strat = CustomEnhancedSQLiteStrategy()
    strat_contrib = StrategyContribution(
        strategy_id=StrategyId("sqlite-connection"),
        authority_id=AuthorityId("connection"),
        provider_id=ProviderId("sqlite"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=InstanceStrategyFactory(custom_strat),
        implementation_version="1.1.0",
        description="Enhanced Custom SQLite Strategy",
    )
    prov_contrib = ProviderContribution(
        provider_id=ProviderId("sqlite"),
        vendor_name="SQLite",
        display_name="Enhanced SQLite",
        family="relational",
        version="1.1.0",
        strategies=(strat_contrib,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("builtin-connection-providers"),
        version="1.1.0",
        display_name="Enhanced SQLite Extension",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        origin=ExtensionOrigin.BUILTIN,
        trust_tier=TrustTier.CORE_TRUSTED,
        provider_contributions=(prov_contrib,),
    )

    # Register replacement
    new_ext_gen = ext_auth.register_extension(manifest, allow_replace=True)
    ext_auth.activate_extension("builtin-connection-providers")

    assert new_ext_gen > initial_ext_gen
    assert conn_cat.get_catalog_generation() > initial_conn_gen

    # Verify that resolving sqlite now returns the enhanced strategy
    handle = ext_auth.resolve_strategy("sqlite", "connection")
    assert handle.implementation_version == "1.1.0"
    assert isinstance(handle.strategy_instance, CustomEnhancedSQLiteStrategy)
    handle.release()
