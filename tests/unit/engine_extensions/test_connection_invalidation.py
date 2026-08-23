"""
tests.unit.engine_extensions.test_connection_invalidation
=========================================================
Tests verifying that Connection pool invalidation coordinates seamlessly when a strategy is updated through Extensions.
"""

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.connection.pooling.invalidation import default_invalidation_coordinator
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


def test_invalidation_triggered_on_connection_strategy_replacement():
    ext_auth = ExtensionsAuthority.get_instance()

    invalidation_broadcasts = []

    def mock_listener(fp, reason):
        invalidation_broadcasts.append((fp, reason))

    default_invalidation_coordinator.register_invalidation_listener(mock_listener)

    try:
        strat = SQLiteProviderStrategy()
        strat_contrib = StrategyContribution(
            strategy_id=StrategyId("sqlite-connection"),
            authority_id=AuthorityId("connection"),
            provider_id=ProviderId("sqlite"),
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=InstanceStrategyFactory(strat),
            implementation_version="1.0.0",
        )
        prov_contrib = ProviderContribution(
            provider_id=ProviderId("sqlite"),
            vendor_name="SQLite",
            display_name="SQLite Provider",
            family="relational",
            strategies=(strat_contrib,),
        )
        manifest = ExtensionManifest(
            extension_id=ExtensionId("builtin-connection-providers"),
            version="1.0.1",
            display_name="SQLite Override Extension",
            engine_version_range=CompatibilityRange(">=1.0.0"),
            origin=ExtensionOrigin.BUILTIN,
            trust_tier=TrustTier.CORE_TRUSTED,
            provider_contributions=(prov_contrib,),
        )

        ext_auth.register_extension(manifest, allow_replace=True)

        # Verify invalidation broadcast was triggered
        assert len(invalidation_broadcasts) >= 1
        last_invalidation = invalidation_broadcasts[-1]
    finally:
        if mock_listener in default_invalidation_coordinator._pool_invalidation_callbacks:
            default_invalidation_coordinator._pool_invalidation_callbacks.remove(mock_listener)
