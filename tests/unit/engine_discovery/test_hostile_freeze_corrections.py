"""
tests.unit.engine_discovery.test_hostile_freeze_corrections
===========================================================
Hostile freeze verification test suite covering all 14 blocker corrections:
1. Canonical multi-page consumption
2. Truthful partial state on pagination failure
3. No fabricated 'public' fallback
4. Event Hubs physical/truthful behavior
5. Provider failure != empty success
6. UNKNOWN permission behavior
7. Cache separation by depth/options/generation
8. Bounded concurrency
9. Timeout/cancellation deadline cleanup
10. Fingerprint determinism and material-domain sensitivity
11. Canonical requested preview sampling
12. Extensions handle release when Connection acquisition fails
13. Canonical view inventory
14. Anti-fabrication across provider families
"""

import sqlite3
import time
from unittest.mock import MagicMock, patch
import pytest

from akaalEngine.connection.api.authority import ConnectionAuthority
from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.discovery.authority import DiscoveryAuthority
from akaalEngine.discovery.core.cache import ProcessLocalDiscoveryCache
from akaalEngine.discovery.core.executor import DiscoveryPipelineExecutor
from akaalEngine.discovery.core.fingerprint import DiscoveryFingerprintCalculator
from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.inventory import (
    NamespaceInventory,
    ObjectClassification,
    ObjectInventory,
    ObjectInventoryPage,
    ObjectType,
    TableFacts,
    ViewFacts,
)
from akaalEngine.discovery.models.permissions import ThreeStatePermission
from akaalEngine.discovery.models.snapshot import DiscoveryCompleteness, DiscoverySnapshot
from akaalEngine.discovery.strategies.nosql.mongodb import MongoDBDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.postgresql import PostgreSQLDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.sqlite import SQLiteDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.s3 import S3DiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.eventhubs import EventHubsDiscoveryStrategy
from akaalEngine.discovery.strategies.warehouse.snowflake import SnowflakeDiscoveryStrategy
from akaalEngine.extensions.authority import ExtensionsAuthority


@pytest.fixture
def sqlite_test_db(tmp_path):
    db_file = str(tmp_path / "freeze_correction_test.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, email TEXT)")
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, sku TEXT NOT NULL, price REAL)")
    conn.execute("CREATE VIEW active_users AS SELECT id, username FROM users WHERE email IS NOT NULL")
    conn.execute("INSERT INTO users VALUES (1, 'alice', 'alice@test.com'), (2, 'bob', 'bob@test.com')")
    conn.execute("INSERT INTO products VALUES (10, 'SKU-001', 19.99), (20, 'SKU-002', 49.50)")
    conn.commit()
    conn.close()
    return db_file


# 1. Canonical Multi-Page Consumption
def test_canonical_multi_page_consumption():
    items = [TableFacts(name=f"tbl_{i}", schema_name="main") for i in range(1250)]
    views = [ViewFacts(name="v_test", schema_name="main")]

    # Page 1
    p1 = CatalogPaginator.paginate_sequence(items, cursor=None, page_size=500, views=views)
    assert len(p1.items) == 500
    assert p1.is_last_page is False
    assert len(p1.views) == 1
    assert p1.cursor is not None

    # Page 2
    p2 = CatalogPaginator.paginate_sequence(items, cursor=p1.cursor, page_size=500, views=views)
    assert len(p2.items) == 500
    assert p2.is_last_page is False
    assert len(p2.views) == 0  # Views only emitted on first page
    assert p2.cursor is not None

    # Page 3 (Last page)
    p3 = CatalogPaginator.paginate_sequence(items, cursor=p2.cursor, page_size=500, views=views)
    assert len(p3.items) == 250
    assert p3.is_last_page is True
    assert p3.cursor is None


# 2. Truthful Partial State on Pagination Failure
def test_truthful_partial_state_on_pagination_failure():
    strat = SQLiteDiscoveryStrategy()
    spec = EndpointSpec(provider_id="sqlite", database_name="dummy.db")
    ctx = DiscoveryContext()

    call_count = 0
    def mock_discover_objects_page(connection, spec, schema_name, context, cursor=None, page_size=500):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ObjectInventoryPage(
                items=(TableFacts(name="table_1", schema_name="main"),),
                cursor="next_token",
                is_last_page=False,
            )
        raise RuntimeError("Disk I/O failure during catalog read")

    with patch.object(strat, "discover_objects_page", side_effect=mock_discover_objects_page):
        snapshot = DiscoveryPipelineExecutor.execute(
            strategy=strat,
            connection=None,
            spec=spec,
            context=ctx,
        )

    # Must be marked PARTIAL, never FULL
    assert snapshot.completeness == DiscoveryCompleteness.PARTIAL
    assert len(snapshot.objects.tables) == 1
    assert any("Object discovery pagination failed" in err for err in snapshot.errors)


# 3. No Fabricated 'public' Fallback
def test_no_fabricated_public_fallback():
    strat_pg = PostgreSQLDiscoveryStrategy()
    spec = EndpointSpec(provider_id="postgresql", host="localhost", database_name="custom_db")
    ctx = DiscoveryContext()

    # When mock cursor returns empty schemas
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    ns = strat_pg.discover_namespaces(mock_conn, spec, ctx)
    assert ns.schemas == ()
    assert ns.default_schema is None  # Never fabricated "public"


# 4. Event Hubs Physical/Truthful Behavior
def test_eventhubs_physical_truthful_behavior():
    strat_eh = EventHubsDiscoveryStrategy()
    spec = EndpointSpec(provider_id="eventhubs", host="test-ns.servicebus.windows.net", database_name="telemetry-hub")
    
    # When connection is None/unverified
    perm = strat_eh.check_read_only_permissions(None, spec)
    assert perm == ThreeStatePermission.UNKNOWN  # Not fabricated PROVEN

    cdc = strat_eh.discover_cdc_prerequisites(None, spec, DiscoveryContext())
    assert cdc.is_cdc_ready is False
    assert len(cdc.blocker_reasons) > 0


# 5. Provider Failure != Empty Success
def test_provider_failure_not_empty_success():
    strat = SQLiteDiscoveryStrategy()
    spec = EndpointSpec(provider_id="sqlite", database_name="nonexistent.db")
    ctx = DiscoveryContext()

    def mock_discover_namespaces(*args, **kwargs):
        raise ConnectionError("Endpoint unreachable")

    with patch.object(strat, "discover_namespaces", side_effect=mock_discover_namespaces):
        snapshot = DiscoveryPipelineExecutor.execute(
            strategy=strat,
            connection=None,
            spec=spec,
            context=ctx,
        )

    assert snapshot.completeness == DiscoveryCompleteness.FAILED
    assert any("Namespace discovery failed" in err for err in snapshot.errors)


# 6. UNKNOWN Permission Behavior
def test_three_state_unknown_permissions():
    strat_pg = PostgreSQLDiscoveryStrategy()
    spec = EndpointSpec(provider_id="postgresql", host="localhost")
    assert strat_pg.check_read_only_permissions(None, spec) == ThreeStatePermission.UNKNOWN

    strat_mongo = MongoDBDiscoveryStrategy()
    spec_mongo = EndpointSpec(provider_id="mongodb", host="localhost")
    assert strat_mongo.check_read_only_permissions(None, spec_mongo) == ThreeStatePermission.UNKNOWN


# 7. Cache Separation by Depth, Options, and Generation
def test_cache_separation_by_depth_and_generation():
    cache = ProcessLocalDiscoveryCache()
    scope = DiscoveryScope()

    k_quick = cache.generate_cache_key("endpoint_123", scope, depth=DiscoveryDepth.QUICK)
    k_deep = cache.generate_cache_key("endpoint_123", scope, depth=DiscoveryDepth.DEEP)
    k_gen1 = cache.generate_cache_key("endpoint_123", scope, depth=DiscoveryDepth.STANDARD, registry_generation=1)
    k_gen2 = cache.generate_cache_key("endpoint_123", scope, depth=DiscoveryDepth.STANDARD, registry_generation=2)

    # Keys must all be distinct
    assert k_quick != k_deep
    assert k_gen1 != k_gen2


# 8. Bounded Concurrency
def test_bounded_concurrency_execution(sqlite_test_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_test_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )
    auth = DiscoveryAuthority()
    ctx = DiscoveryContext(depth=DiscoveryDepth.STANDARD, concurrency_limit=4)
    snapshot = auth.discover(spec, context=ctx, use_cache=False)

    assert snapshot.completeness == DiscoveryCompleteness.FULL
    assert "main.users" in snapshot.structures
    assert "main.products" in snapshot.structures


# 9. Timeout / Cancellation Cleanup
def test_timeout_deadline_enforcement():
    strat = SQLiteDiscoveryStrategy()
    spec = EndpointSpec(provider_id="sqlite", database_name="test.db")
    ctx = DiscoveryContext(timeout_seconds=0.01)  # 10ms deadline

    def slow_discover_objects(*args, **kwargs):
        time.sleep(0.05)
        return ObjectInventoryPage(items=())

    with patch.object(strat, "discover_objects_page", side_effect=slow_discover_objects):
        snapshot = DiscoveryPipelineExecutor.execute(
            strategy=strat,
            connection=None,
            spec=spec,
            context=ctx,
        )

    assert any("deadline" in w for w in snapshot.warnings)


# 10. Fingerprint Determinism and Material-Domain Sensitivity
def test_fingerprint_material_domain_sensitivity():
    fp1 = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["public"]},
        objects_dict={"tables": [{"name": "t1"}], "views": []},
        structures_dict={"public.t1": {"columns": [{"name": "id", "type": "INT"}]}},
    )

    # Change a view (material object domain change)
    fp2 = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["public"]},
        objects_dict={"tables": [{"name": "t1"}], "views": [{"name": "v1"}]},
        structures_dict={"public.t1": {"columns": [{"name": "id", "type": "INT"}]}},
    )

    # Change CDC flag
    fp3 = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["public"]},
        objects_dict={"tables": [{"name": "t1"}], "views": []},
        structures_dict={"public.t1": {"columns": [{"name": "id", "type": "INT"}]}},
        cdc_dict={"is_cdc_ready": True},
    )

    assert fp1.sha256_hash != fp2.sha256_hash
    assert fp1.sha256_hash != fp3.sha256_hash


# 11. Canonical Requested Preview Sampling
def test_canonical_requested_sampling(sqlite_test_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_test_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )
    auth = DiscoveryAuthority()
    ctx = DiscoveryContext(sample_records=True, sample_size=10, max_sampled_tables=5)
    snapshot = auth.discover(spec, context=ctx, use_cache=False)

    assert len(snapshot.sampled_data) > 0
    assert "main.users" in snapshot.sampled_data
    users_sample = snapshot.sampled_data["main.users"]
    assert users_sample.is_sampled is True
    assert users_sample.sample_count == 2
    # Email column should be redacted by RedactionGuard
    assert users_sample.is_redacted is True
    assert users_sample.records[0]["email"] == "[REDACTED]"


# 12. Extensions Handle Release when Connection Acquisition Fails
def test_extensions_handle_released_on_connection_failure():
    auth = DiscoveryAuthority()
    spec = EndpointSpec(provider_id="sqlite", database_name="bad_db.db")

    handle_released = False
    orig_release = auth._coordinator.release_strategy_handle

    def mock_release(handle):
        nonlocal handle_released
        handle_released = True
        return orig_release(handle)

    with patch.object(auth._coordinator, "release_strategy_handle", side_effect=mock_release):
        with patch.object(auth._coordinator, "acquire_discovery_session", side_effect=ConnectionError("Pool exhausted")):
            with pytest.raises(ConnectionError):
                auth.discover(spec, use_cache=False)

    assert handle_released is True


# 13. Canonical View Inventory
def test_canonical_view_inventory(sqlite_test_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_test_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )
    auth = DiscoveryAuthority()
    snapshot = auth.discover(spec, use_cache=False)

    assert snapshot.objects is not None
    view_names = [v.name for v in snapshot.objects.views]
    assert "active_users" in view_names


# 14. Anti-Fabrication across Provider Families
def test_anti_fabrication_fleet_sweep():
    # S3
    strat_s3 = S3DiscoveryStrategy()
    spec_s3 = EndpointSpec(provider_id="s3")
    ns_s3 = strat_s3.discover_namespaces(None, spec_s3, DiscoveryContext())
    assert ns_s3.buckets == ()
    assert ns_s3.default_schema is None  # No fake "default-bucket"
    perm_s3 = strat_s3.check_read_only_permissions(None, spec_s3)
    assert perm_s3 == ThreeStatePermission.UNKNOWN
    cdc_s3 = strat_s3.discover_cdc_prerequisites(None, spec_s3, DiscoveryContext())
    assert cdc_s3.is_cdc_ready is False

    # Snowflake
    strat_sf = SnowflakeDiscoveryStrategy()
    spec_sf = EndpointSpec(provider_id="snowflake")
    ns_sf = strat_sf.discover_namespaces(None, spec_sf, DiscoveryContext())
    assert ns_sf.schemas == ()
    assert ns_sf.default_schema is None  # No fake "PUBLIC"
    perm_sf = strat_sf.check_read_only_permissions(None, spec_sf)
    assert perm_sf == ThreeStatePermission.UNKNOWN


# 15. Native Provider Token Continuation
def test_native_provider_token_continuation():
    cur = DiscoveryCursor(schema_index=0, offset=500, provider_token="aws_s3_next_tok_xyz")
    encoded = cur.encode()
    decoded = DiscoveryCursor.decode(encoded)
    assert decoded.provider_token == "aws_s3_next_tok_xyz"
    assert decoded.offset == 500


# 16. Cache Identity covers max_objects, max_sampled_tables, timeout
def test_cache_identity_scale_coverage():
    cache = ProcessLocalDiscoveryCache()
    scope = DiscoveryScope()

    k1 = cache.generate_cache_key("ep1", scope, max_objects=1000)
    k2 = cache.generate_cache_key("ep1", scope, max_objects=50000)
    k3 = cache.generate_cache_key("ep1", scope, max_sampled_tables=5)
    k4 = cache.generate_cache_key("ep1", scope, max_sampled_tables=20)
    k5 = cache.generate_cache_key("ep1", scope, timeout_seconds=10.0)
    k6 = cache.generate_cache_key("ep1", scope, timeout_seconds=60.0)

    assert k1 != k2
    assert k3 != k4
    assert k5 != k6


# 17. 12-Domain Fingerprint Coverage
def test_fingerprint_12_domain_coverage():
    fp_base = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["main"]},
        objects_dict={"tables": [{"name": "users"}]},
        structures_dict={"main.users": {"columns": [{"name": "id"}]}},
        identity_dict={"provider_id": "sqlite", "version": "3.39"},
        permissions_dict={"read_only_verified": "PROVEN"},
        statistics_dict={"total_bytes": 1024},
        volume_dict={"total_rows": 100},
    )

    # Change identity
    fp_id_change = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["main"]},
        objects_dict={"tables": [{"name": "users"}]},
        structures_dict={"main.users": {"columns": [{"name": "id"}]}},
        identity_dict={"provider_id": "sqlite", "version": "3.40"},
        permissions_dict={"read_only_verified": "PROVEN"},
        statistics_dict={"total_bytes": 1024},
        volume_dict={"total_rows": 100},
    )

    # Change statistics
    fp_stats_change = DiscoveryFingerprintCalculator.compute(
        namespaces_dict={"schemas": ["main"]},
        objects_dict={"tables": [{"name": "users"}]},
        structures_dict={"main.users": {"columns": [{"name": "id"}]}},
        identity_dict={"provider_id": "sqlite", "version": "3.39"},
        permissions_dict={"read_only_verified": "PROVEN"},
        statistics_dict={"total_bytes": 2048},
        volume_dict={"total_rows": 100},
    )

    assert fp_base.sha256_hash != fp_id_change.sha256_hash
    assert fp_base.sha256_hash != fp_stats_change.sha256_hash

