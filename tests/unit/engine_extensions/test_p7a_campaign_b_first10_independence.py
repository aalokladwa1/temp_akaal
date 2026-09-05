"""
tests.unit.engine_extensions.test_p7a_campaign_b_first10_independence
=========================================================================
P7A Campaign B — First-10-Provider Independence Hardening Gate.

Hostile cross-cutting tests for the first 10 Campaign B providers (CockroachDB,
RabbitMQ, Pulsar, DynamoDB, Couchbase, ClickHouse, InfluxDB, YugabyteDB, TiDB,
SingleStore) proving:
  1. None of them can silently acquire a physical CDC adapter through the CDC
     authority (Authority #10) when they declared CDC_LOG_CAPTURE=UNSUPPORTED and
     have registered no "cdc" StrategyContribution -- negative capability truth
     must be an enforcement contract, not documentation.
  2. Provider identity resolution cannot collapse into a different provider's
     strategy (e.g. resolving "cockroachdb" must never return the PostgreSQL
     strategy instance, "tidb"/"singlestore" must never return the MySQL strategy
     instance, "yugabytedb" must never return the PostgreSQL strategy instance).
  3. Inherited discovery behavior (CockroachDB/YugabyteDB from PostgresDiscoveryStrategy,
     TiDB/SingleStore from MySQLDiscoveryStrategy) is overridden exactly where the
     provider is genuinely different, and each subclass reports its OWN provider_id,
     not the parent's.
"""

from __future__ import annotations

import pytest

NEW_PROVIDERS = [
    "cockroachdb", "rabbitmq", "pulsar", "dynamodb", "couchbase",
    "clickhouse", "influxdb", "yugabytedb", "tidb", "singlestore",
]

WIRE_COMPATIBLE_INHERITORS = {
    "cockroachdb": "postgresql",
    "yugabytedb": "postgresql",
    "tidb": "mysql",
    "singlestore": "mysql",
}


def _fresh_discovery_authority():
    # Explicitly bind to the CURRENT live ExtensionsAuthority singleton (via get_instance(),
    # not a module-level `default_extensions_authority` import) -- other test modules in this
    # suite call ExtensionsAuthority.reset_instance(), which would otherwise leave a stale
    # imported reference and cause this test to see an ExtensionsAuthority instance whose
    # connection-provider manifest was never adopted, purely due to test run order.
    from akaalEngine.discovery.authority import DiscoveryAuthority
    from akaalEngine.extensions.authority import ExtensionsAuthority

    ext_auth = ExtensionsAuthority.get_instance()
    ext_auth.bootstrap_builtin_providers()
    return DiscoveryAuthority(extensions_authority=ext_auth)


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_cdc_authority_fails_closed_for_undeclared_cdc_provider(provider_id):
    """None of the first-10 providers registered a 'cdc' StrategyContribution
    (all declared CDC_LOG_CAPTURE=UNSUPPORTED at rest), so resolving a CDC adapter
    for any of them through the real CDCAuthority.resolve_adapter_for_provider()
    path must fail closed with StrategyNotFoundError -- proving a negative capability
    cannot be silently bypassed to instantiate physical CDC capture behavior."""
    from akaalEngine.cdc.api import CDCAuthority
    from akaalEngine.extensions.errors.taxonomy import ExtensionEngineException

    da = _fresh_discovery_authority()
    cdc = CDCAuthority(extensions_authority=da._ext_auth)

    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider(provider_id)


@pytest.mark.parametrize("provider_id,parent_provider_id", WIRE_COMPATIBLE_INHERITORS.items())
def test_connection_provider_identity_does_not_collapse_into_parent(provider_id, parent_provider_id):
    """CockroachDB/YugabyteDB (psycopg2-based, like PostgreSQL) and TiDB/SingleStore
    (PyMySQL-based, like MySQL) must resolve to their OWN connection strategy
    instance, never silently falling back to or aliasing the wire-protocol-compatible
    parent provider's strategy."""
    from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog

    catalog = ProviderCatalog.get_instance()
    own_strategy = catalog.get_strategy(provider_id)
    parent_strategy = catalog.get_strategy(parent_provider_id)

    assert own_strategy is not parent_strategy
    assert type(own_strategy) is not type(parent_strategy)
    assert own_strategy.PROVIDER_ID == provider_id
    assert own_strategy.get_static_manifest().provider_id == provider_id


@pytest.mark.parametrize("provider_id,parent_provider_id", WIRE_COMPATIBLE_INHERITORS.items())
def test_discovery_provider_identity_does_not_collapse_into_parent(provider_id, parent_provider_id):
    """Discovery strategies for the 4 wire-compatible-driver providers must report
    their OWN provider_id even though they subclass the parent's discovery strategy
    class (PostgresDiscoveryStrategy / MySQLDiscoveryStrategy) for catalog-query reuse."""
    from akaalEngine.discovery.strategies import ALL_DISCOVERY_STRATEGIES

    strat_map = {s().provider_id: s for s in ALL_DISCOVERY_STRATEGIES}
    own_cls = strat_map[provider_id]
    parent_cls = strat_map[parent_provider_id]

    own_instance = own_cls()
    parent_instance = parent_cls()

    assert own_instance.provider_id == provider_id
    assert parent_instance.provider_id == parent_provider_id
    assert own_instance.provider_id != parent_instance.provider_id
    # Subclassing for catalog-query reuse is legitimate; identity collapse is not.
    assert issubclass(own_cls, parent_cls) or provider_id in ("rabbitmq", "pulsar", "dynamodb", "couchbase", "clickhouse", "influxdb")


def test_all_ten_new_providers_registered_with_unique_identity_no_collision():
    """Each of the 10 new providers must be a distinct, uniquely-identified entry in
    the live ProviderCatalog with no collision against any of the original 28 or
    each other."""
    from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog

    catalog = ProviderCatalog.get_instance()
    all_ids = catalog.list_providers()

    assert len(all_ids) == len(set(all_ids)), "provider catalog contains duplicate provider_id entries"
    for p in NEW_PROVIDERS:
        assert p in all_ids, f"'{p}' missing from live ProviderCatalog"

    # Fleet floor, not a frozen literal -- prefer dynamic growth-tolerant assertions.
    assert len(all_ids) >= 38


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_extensions_authority_capability_truth_matches_static_manifest(provider_id):
    """The capability declarations visible through ExtensionsAuthority (what Pipeline/
    Gateway actually see) must match the provider's own static manifest exactly --
    proving capability truth propagates correctly from the provider strategy through
    the shared Extensions/adoption machinery without silent drift."""
    from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog
    from akaalEngine.extensions.integration.builtin_connection_bootstrap import BUILTIN_CONNECTION_EXTENSION_ID

    da = _fresh_discovery_authority()
    catalog = ProviderCatalog.get_instance()
    strategy = catalog.get_strategy(provider_id)
    manifest_caps = strategy.get_static_manifest().capabilities

    snap = da._ext_auth._registry.get_snapshot()
    ext_manifest = snap.get_extension(BUILTIN_CONNECTION_EXTENSION_ID)
    contrib = next(p for p in ext_manifest.provider_contributions if p.provider_id.value == provider_id)
    ext_caps = {c.capability_name: c.is_supported for c in contrib.capabilities}

    for cap_name, status in manifest_caps.items():
        expected_supported = (status.value == "SUPPORTED") if hasattr(status, "value") else (str(status) == "SUPPORTED")
        assert cap_name in ext_caps, f"'{provider_id}' capability '{cap_name}' missing from ExtensionsAuthority view"
        assert ext_caps[cap_name] == expected_supported, (
            f"'{provider_id}' capability '{cap_name}' drifted: manifest={expected_supported}, extensions={ext_caps[cap_name]}"
        )


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_certification_obligations_are_capability_derived_not_hardcoded(provider_id):
    """Certification obligations for each of the 10 new providers must be computed from
    that provider's own declared capabilities (data-driven), not from a hard-coded
    provider taxonomy -- proving certification independence: a provider that declares
    fewer capabilities (e.g. RabbitMQ, which does not declare SCHEMA_DISCOVERY the way
    relational/NoSQL providers do) must receive a correspondingly smaller obligation set,
    never a copy-pasted universal set that silently assumes relational-style capabilities."""
    from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog
    from akaalEngine.extensions.certification.profiles import build_profile_for_capabilities

    catalog = ProviderCatalog.get_instance()
    strategy = catalog.get_strategy(provider_id)
    manifest = strategy.get_static_manifest()
    supported = [
        name for name, status in manifest.capabilities.items()
        if (status.value if hasattr(status, "value") else str(status)) == "SUPPORTED"
    ]

    profile = build_profile_for_capabilities(supported, name=provider_id)
    assert len(profile.obligations) > 0

    # A provider that does NOT declare SCHEMA_DISCOVERY must not receive a
    # DISCOVERY_SCHEMA-category obligation manufactured out of thin air.
    from akaalEngine.extensions.certification.obligations import ObligationCategory
    obligation_categories = {o.category for o in profile.obligations}
    if "SCHEMA_DISCOVERY" not in supported:
        assert ObligationCategory.DISCOVERY_SCHEMA not in obligation_categories, (
            f"'{provider_id}' did not declare SCHEMA_DISCOVERY but received a DISCOVERY_SCHEMA obligation anyway"
        )
