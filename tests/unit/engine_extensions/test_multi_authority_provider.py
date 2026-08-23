"""
tests.unit.engine_extensions.test_multi_authority_provider
==========================================================
Tests verifying that a single ProviderBundle can supply distinct strategies to multiple Engine Authorities
(Connection, Discovery, Schema, Transport, CDC, Validation) without collapsing into a universal provider superclass.
"""

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
from akaalEngine.extensions.spi.provider_bundle import ProviderBundle
from akaalEngine.extensions.spi.authority_contract import (
    AuthorityContractDefinition,
    default_contract_registry,
)


class MockPostgresDiscoveryStrategy:
    def discover(self): return "discovered"

class MockPostgresSchemaStrategy:
    def extract_ddl(self): return "CREATE TABLE..."

class MockPostgresTransportStrategy:
    def read_stream(self): return [1, 2, 3]

class MockPostgresCDCStrategy:
    def capture_stream(self): return "cdc_events"

class MockPostgresValidationStrategy:
    def hash_dataset(self): return "hash_val"


def test_multi_authority_provider_bundle():
    ext_auth = ExtensionsAuthority.get_instance()

    # Register contracts for future authorities
    for auth_name in ("discovery", "schema", "transport", "change_capture", "validation"):
        default_contract_registry.register_contract(
            AuthorityContractDefinition(
                authority_id=AuthorityId(auth_name),
                contract_version="1.0.0",
                description=f"Contract for {auth_name}",
            )
        )

    prov_id = ProviderId("postgresql_multi")

    strategies = (
        StrategyContribution(
            strategy_id=StrategyId("pg-disc-strat"),
            authority_id=AuthorityId("discovery"),
            provider_id=prov_id,
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=MockPostgresDiscoveryStrategy,
        ),
        StrategyContribution(
            strategy_id=StrategyId("pg-schema-strat"),
            authority_id=AuthorityId("schema"),
            provider_id=prov_id,
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=MockPostgresSchemaStrategy,
        ),
        StrategyContribution(
            strategy_id=StrategyId("pg-transport-strat"),
            authority_id=AuthorityId("transport"),
            provider_id=prov_id,
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=MockPostgresTransportStrategy,
        ),
        StrategyContribution(
            strategy_id=StrategyId("pg-cdc-strat"),
            authority_id=AuthorityId("change_capture"),
            provider_id=prov_id,
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=MockPostgresCDCStrategy,
        ),
        StrategyContribution(
            strategy_id=StrategyId("pg-valid-strat"),
            authority_id=AuthorityId("validation"),
            provider_id=prov_id,
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=MockPostgresValidationStrategy,
        ),
    )

    bundle = ProviderBundle(
        provider_id=prov_id,
        vendor_name="PostgreSQL",
        display_name="Multi-Authority PostgreSQL",
        family="relational",
        strategies=strategies,
    )

    manifest = ExtensionManifest(
        extension_id=ExtensionId("pg-multi-bundle-ext"),
        version="1.0.0",
        display_name="PostgreSQL Multi-Authority Bundle",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(bundle.to_contribution(),),
    )

    ext_auth.register_extension(manifest, allow_replace=True)
    ext_auth.activate_extension("pg-multi-bundle-ext")

    # Verify that each distinct authority strategy resolves correctly under the same provider identity
    h_disc = ext_auth.resolve_strategy("postgresql_multi", "discovery")
    assert isinstance(h_disc.strategy_instance, MockPostgresDiscoveryStrategy)
    h_disc.release()

    h_schema = ext_auth.resolve_strategy("postgresql_multi", "schema")
    assert isinstance(h_schema.strategy_instance, MockPostgresSchemaStrategy)
    h_schema.release()

    h_trans = ext_auth.resolve_strategy("postgresql_multi", "transport")
    assert isinstance(h_trans.strategy_instance, MockPostgresTransportStrategy)
    h_trans.release()

    h_cdc = ext_auth.resolve_strategy("postgresql_multi", "change_capture")
    assert isinstance(h_cdc.strategy_instance, MockPostgresCDCStrategy)
    h_cdc.release()

    h_valid = ext_auth.resolve_strategy("postgresql_multi", "validation")
    assert isinstance(h_valid.strategy_instance, MockPostgresValidationStrategy)
    h_valid.release()
