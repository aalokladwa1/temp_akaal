"""
tests.unit.engine_discovery.test_final_three_blockers
=====================================================
Comprehensive validation for the 3 consolidated freeze blockers:
1. Physical Truth for Permissions, CDC Mechanisms, and Declared Facts
2. Empty Must Never Mean Failed (0-row physical table vs sampling error)
3. Enterprise 50,000+ Object Execution (bulk catalog queries, bounded queries, server-side cursors)
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.discovery.core.executor import DiscoveryPipelineExecutor
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectInventoryPage, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.snapshot import DiscoveryCompleteness
from akaalEngine.discovery.models.statistics import TableSizeFacts
from akaalEngine.discovery.models.structure import ObjectStructureFacts
from akaalEngine.discovery.strategies.nosql.cassandra import CassandraDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.elasticsearch import ElasticsearchDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.mongodb import MongoDBDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.neo4j import Neo4jDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.opensearch import OpenSearchDiscoveryStrategy
from akaalEngine.discovery.strategies.nosql.redis import RedisDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.ibm_db2 import IBMDb2DiscoveryStrategy
from akaalEngine.discovery.strategies.relational.mssql import MSSQLDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.mysql import MySQLDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.oracle import OracleDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.postgresql import PostgresDiscoveryStrategy
from akaalEngine.discovery.strategies.relational.sqlite import SQLiteDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.azure_blob import AzureBlobDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.gcs import GCSDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.hdfs import HDFSDiscoveryStrategy
from akaalEngine.discovery.strategies.storage.s3 import S3DiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.eventhubs import EventHubsDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.kafka import KafkaDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.kinesis import KinesisDiscoveryStrategy
from akaalEngine.discovery.strategies.streaming.pubsub import PubSubDiscoveryStrategy
from akaalEngine.discovery.strategies.warehouse.bigquery import BigQueryDiscoveryStrategy
from akaalEngine.discovery.strategies.warehouse.databricks import DatabricksDiscoveryStrategy
from akaalEngine.discovery.strategies.warehouse.redshift import RedshiftDiscoveryStrategy
from akaalEngine.discovery.strategies.warehouse.snowflake import SnowflakeDiscoveryStrategy


def _make_spec(provider_id: str) -> EndpointSpec:
    return EndpointSpec(
        provider_id=provider_id,
        host="test-host",
        database_name="testdb",
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )


# ==============================================================================
# BLOCKER 1: PHYSICAL TRUTH FOR PERMISSIONS / CDC / DECLARED FACTS
# ==============================================================================

def test_read_only_verified_never_inferred_from_metadata_read():
    """Metadata read / SELECT 1 must NEVER imply read_only_verified is PROVEN."""
    # Streaming engines
    assert KinesisDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("kinesis")) == ThreeStatePermission.UNKNOWN
    assert PubSubDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("pubsub")) == ThreeStatePermission.UNKNOWN
    assert EventHubsDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("eventhubs")) == ThreeStatePermission.UNKNOWN
    assert KafkaDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("kafka")) == ThreeStatePermission.UNKNOWN

    # Cloud Storage engines
    assert S3DiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("s3")) == ThreeStatePermission.UNKNOWN
    assert GCSDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("gcs")) == ThreeStatePermission.UNKNOWN
    assert AzureBlobDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("azure_blob")) == ThreeStatePermission.UNKNOWN
    assert HDFSDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("hdfs")) == ThreeStatePermission.UNKNOWN

    # Warehouses
    assert SnowflakeDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("snowflake")) == ThreeStatePermission.UNKNOWN
    assert BigQueryDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("bigquery")) == ThreeStatePermission.UNKNOWN
    assert DatabricksDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("databricks")) == ThreeStatePermission.UNKNOWN

    # NoSQL
    assert MongoDBDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("mongodb")) == ThreeStatePermission.UNKNOWN
    assert CassandraDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("cassandra")) == ThreeStatePermission.UNKNOWN
    assert RedisDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("redis")) == ThreeStatePermission.UNKNOWN
    assert Neo4jDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("neo4j")) == ThreeStatePermission.UNKNOWN
    assert ElasticsearchDiscoveryStrategy().check_read_only_permissions(MagicMock(), _make_spec("elasticsearch")) == ThreeStatePermission.UNKNOWN


def test_native_cdc_mechanisms_truthfully_classified():
    """Streaming, Warehouse, and NoSQL engines report truthful native CDC mechanisms."""
    ctx = DiscoveryContext()
    mock_conn = MagicMock()

    # Kinesis
    kinesis_cdc = KinesisDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("kinesis"), ctx)
    assert kinesis_cdc.mechanism == CDCMechanism.KINESIS_DATA_STREAMS

    # PubSub
    pubsub_cdc = PubSubDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("pubsub"), ctx)
    assert pubsub_cdc.mechanism == CDCMechanism.GCP_PUBSUB

    # EventHubs
    mock_eh_conn = MagicMock()
    mock_eh_conn.get_eventhub_properties.return_value = {"name": "eh"}
    eh_cdc = EventHubsDiscoveryStrategy().discover_cdc_prerequisites(mock_eh_conn, _make_spec("eventhubs"), ctx)
    assert eh_cdc.mechanism == CDCMechanism.AZURE_EVENT_HUBS

    # Snowflake
    sf_cdc = SnowflakeDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("snowflake"), ctx)
    assert sf_cdc.mechanism == CDCMechanism.SNOWFLAKE_STREAMS

    # BigQuery
    bq_cdc = BigQueryDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("bigquery"), ctx)
    assert bq_cdc.mechanism == CDCMechanism.BIGQUERY_CDC

    # Databricks
    db_cdc = DatabricksDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("databricks"), ctx)
    assert db_cdc.mechanism == CDCMechanism.DELTA_CHANGE_DATA_FEED

    # Cassandra
    cas_cdc = CassandraDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("cassandra"), ctx)
    assert cas_cdc.mechanism == CDCMechanism.CASSANDRA_CDC

    # Redis
    redis_cdc = RedisDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("redis"), ctx)
    assert redis_cdc.mechanism == CDCMechanism.REDIS_STREAMS_CDC

    # Elasticsearch & OpenSearch
    es_cdc = ElasticsearchDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("elasticsearch"), ctx)
    assert es_cdc.mechanism == CDCMechanism.ELASTICSEARCH_CHANGES
    os_cdc = OpenSearchDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("opensearch"), ctx)
    assert os_cdc.mechanism == CDCMechanism.OPENSEARCH_CHANGES

    # Neo4j
    neo_cdc = Neo4jDiscoveryStrategy().discover_cdc_prerequisites(mock_conn, _make_spec("neo4j"), ctx)
    assert neo_cdc.mechanism == CDCMechanism.NEO4J_CDC


# ==============================================================================
# BLOCKER 2: EMPTY MUST NEVER MEAN FAILED (0 ROWS vs FAILED SAMPLING)
# ==============================================================================

def test_sampling_empty_table_vs_failure_distinction():
    """Physically empty table has is_sampled=True, count=0; failed sampling has is_sampled=False, error_message set."""
    # 1. Empty table physically sampled successfully
    empty_sample = DeterministicSampler.package_sample(
        table_name="empty_tbl",
        schema_name="public",
        column_names=["id", "name"],
        raw_records=[],
    )
    assert empty_sample.is_sampled is True
    assert empty_sample.sample_count == 0
    assert empty_sample.error_message is None
    assert empty_sample.records == ()

    # 2. Failed sampling operation (timeout / connection reset)
    failed_sample = DeterministicSampler.package_failure(
        table_name="error_tbl",
        schema_name="public",
        error_message="Query timed out after 3.0 seconds",
    )
    assert failed_sample.is_sampled is False
    assert failed_sample.sample_count == 0
    assert "timed out" in (failed_sample.error_message or "")
    assert failed_sample.records == ()


def test_strategy_sampling_exception_generates_package_failure():
    """When strategy sampling throws an exception, it packages a truthful failure record."""
    strat = PostgresDiscoveryStrategy()
    spec = _make_spec("postgresql")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.execute.side_effect = RuntimeError("canceling statement due to statement timeout")

    sample = strat.sample_data(mock_conn, spec, "public", "big_table", limit=100)
    assert sample.is_sampled is False
    assert sample.sample_count == 0
    assert "statement timeout" in (sample.error_message or "")


# ==============================================================================
# BLOCKER 3: ENTERPRISE 50,000+ OBJECT EXECUTION & BULK DISCOVERY
# ==============================================================================

def test_bulk_structure_and_statistics_reduces_n_plus_one():
    """500-table batch executed in bounded queries via discover_objects_structure_bulk and discover_table_statistics_bulk."""
    strat = PostgresDiscoveryStrategy()
    spec = _make_spec("postgresql")
    ctx = DiscoveryContext(depth=DiscoveryDepth.STANDARD)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Setup 500 table names
    table_names = [f"table_{i}" for i in range(500)]

    # Mock cursor responses for bulk columns, bulk constraints, bulk indexes
    col_rows = [(f"table_{i}", 1, "id", "bigint", True, None, "", "") for i in range(500)]
    con_rows = [(f"table_{i}", f"pk_table_{i}", "p", "PRIMARY KEY (id)", ["id"], None, None, None, None, None, False, False) for i in range(500)]
    idx_rows = [(f"table_{i}", f"pk_table_{i}", "btree", True, True, f"CREATE UNIQUE INDEX pk_table_{i} ON table_{i} (id)", ["id"]) for i in range(500)]

    mock_cursor.fetchall.side_effect = [col_rows, con_rows, idx_rows]

    bulk_structs = strat.discover_objects_structure_bulk(mock_conn, spec, "public", table_names, ctx)
    
    assert len(bulk_structs) == 500
    assert "table_0" in bulk_structs
    assert "table_499" in bulk_structs
    assert bulk_structs["table_0"].primary_key is not None
    assert bulk_structs["table_0"].primary_key.name == "pk_table_0"
    assert len(bulk_structs["table_0"].columns) == 1

    # Only 3 SQL queries were executed for 500 tables instead of 1,500 individual queries!
    assert mock_cursor.execute.call_count == 3


def test_bulk_statistics_discovery_bounded_queries():
    """Bulk statistics query returns size facts for all 500 tables in 1 SQL query."""
    strat = PostgresDiscoveryStrategy()
    spec = _make_spec("postgresql")
    ctx = DiscoveryContext()

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    table_names = [f"table_{i}" for i in range(500)]
    stat_rows = [(f"table_{i}", 10000, 8192000, 1024000, 0) for i in range(500)]
    mock_cursor.fetchall.return_value = stat_rows

    bulk_stats = strat.discover_table_statistics_bulk(mock_conn, spec, "public", table_names, ctx)
    assert len(bulk_stats) == 500
    assert bulk_stats["table_250"].row_count == 10000
    assert bulk_stats["table_250"].data_bytes == 8192000
    assert mock_cursor.execute.call_count == 1


def test_executor_chunked_batch_processing_large_catalog():
    """Executor batches 1,000 discovered tables in 500-table chunks for bulk inspection."""
    strat = PostgresDiscoveryStrategy()
    spec = _make_spec("postgresql")
    ctx = DiscoveryContext(depth=DiscoveryDepth.STANDARD, sample_records=False)

    # 1,000 tables in public schema
    page_1_tables = [TableFacts(name=f"table_{i}", schema_name="public") for i in range(500)]
    page_2_tables = [TableFacts(name=f"table_{i}", schema_name="public") for i in range(500, 1000)]

    strat.discover_namespaces = MagicMock(return_value=NamespaceInventory(schemas=("public",)))
    strat.discover_objects_page = MagicMock(side_effect=[
        ObjectInventoryPage(items=tuple(page_1_tables), cursor="page2", is_last_page=False),
        ObjectInventoryPage(items=tuple(page_2_tables), cursor=None, is_last_page=True),
    ])

    chunk_1_structs = {f"table_{i}": ObjectStructureFacts(table_name=f"table_{i}", schema_name="public") for i in range(500)}
    chunk_2_structs = {f"table_{i}": ObjectStructureFacts(table_name=f"table_{i}", schema_name="public") for i in range(500, 1000)}
    strat.discover_objects_structure_bulk = MagicMock(side_effect=[chunk_1_structs, chunk_2_structs])

    chunk_1_stats = {f"table_{i}": TableSizeFacts(table_name=f"table_{i}", schema_name="public", row_count=100) for i in range(500)}
    chunk_2_stats = {f"table_{i}": TableSizeFacts(table_name=f"table_{i}", schema_name="public", row_count=100) for i in range(500, 1000)}
    strat.discover_table_statistics_bulk = MagicMock(side_effect=[chunk_1_stats, chunk_2_stats])

    strat.discover_permissions = MagicMock(return_value=PermissionAssessment())
    strat.discover_topology = MagicMock(return_value=None)
    strat.discover_cdc_prerequisites = MagicMock(return_value=None)
    strat.discover_environment = MagicMock(return_value=None)
    strat.get_schema_change_marker = MagicMock(return_value="marker1")

    mock_conn = MagicMock()
    snapshot = DiscoveryPipelineExecutor.execute(strat, mock_conn, spec, ctx)

    assert snapshot.completeness == DiscoveryCompleteness.FULL
    assert len(snapshot.objects.tables) == 1000
    assert len(snapshot.structures) == 1000
    assert "public.table_0" in snapshot.structures
    assert "public.table_999" in snapshot.structures

    # Verify that bulk structure and bulk statistics were dispatched in exactly 2 chunks (500 each)
    assert strat.discover_objects_structure_bulk.call_count == 2
    assert strat.discover_table_statistics_bulk.call_count == 2
    assert len(strat.discover_objects_structure_bulk.call_args_list[0].kwargs["object_names"]) == 500
    assert len(strat.discover_objects_structure_bulk.call_args_list[1].kwargs["object_names"]) == 500


def test_kinesis_and_pubsub_active_cdc_probes():
    """Kinesis & PubSub perform active physical probes rather than checking hasattr."""
    ctx = DiscoveryContext()

    # 1. Kinesis - failure during list_streams probe
    mock_kin_conn = MagicMock()
    mock_kin_conn.list_streams.side_effect = RuntimeError("AccessDenied: User is not authorized")
    kinesis_cdc = KinesisDiscoveryStrategy().discover_cdc_prerequisites(mock_kin_conn, _make_spec("kinesis"), ctx)
    assert kinesis_cdc.is_cdc_ready is False
    assert "AccessDenied" in kinesis_cdc.blocker_reasons[0]

    # 2. Kinesis - active stream status verification
    mock_kin_conn2 = MagicMock()
    mock_kin_conn2.list_streams.return_value = {"StreamNames": ["stream1"]}
    mock_kin_conn2.describe_stream_summary.return_value = {"StreamDescriptionSummary": {"StreamStatus": "CREATING"}}
    spec_with_stream = EndpointSpec(provider_id="kinesis", database_name="stream1")
    kinesis_cdc2 = KinesisDiscoveryStrategy().discover_cdc_prerequisites(mock_kin_conn2, spec_with_stream, ctx)
    assert kinesis_cdc2.is_cdc_ready is False
    assert "status is 'CREATING'" in kinesis_cdc2.blocker_reasons[0]

    # 3. Kinesis - active stream probe passes
    mock_kin_conn3 = MagicMock()
    mock_kin_conn3.list_streams.return_value = {"StreamNames": ["stream1"]}
    mock_kin_conn3.describe_stream_summary.return_value = {"StreamDescriptionSummary": {"StreamStatus": "ACTIVE"}}
    kinesis_cdc3 = KinesisDiscoveryStrategy().discover_cdc_prerequisites(mock_kin_conn3, spec_with_stream, ctx)
    assert kinesis_cdc3.is_cdc_ready is True

    # 4. PubSub - failure during list_topics probe
    mock_ps_conn = MagicMock()
    mock_ps_conn.list_topics.side_effect = RuntimeError("Permission denied on resource")
    pubsub_cdc = PubSubDiscoveryStrategy().discover_cdc_prerequisites(mock_ps_conn, _make_spec("pubsub"), ctx)
    assert pubsub_cdc.is_cdc_ready is False
    assert "Permission denied" in pubsub_cdc.blocker_reasons[0]

    # 5. PubSub - probe passes
    mock_ps_conn2 = MagicMock()
    mock_ps_conn2.list_topics.return_value = []
    pubsub_cdc2 = PubSubDiscoveryStrategy().discover_cdc_prerequisites(mock_ps_conn2, _make_spec("pubsub"), ctx)
    assert pubsub_cdc2.is_cdc_ready is True


def test_provider_failures_propagate_to_executor_and_mark_degraded_or_partial():
    """Provider physical failures raise exceptions and are captured as errors/degraded status in executor."""
    ctx = DiscoveryContext(depth=DiscoveryDepth.QUICK)

    # 1. PubSub namespace failure
    ps_strat = PubSubDiscoveryStrategy()
    ps_conn = MagicMock()
    ps_conn.list_topics.side_effect = RuntimeError("PubSub 403 Forbidden")
    snap_ps = DiscoveryPipelineExecutor.execute(ps_strat, ps_conn, _make_spec("pubsub"), ctx)
    assert any("Namespace discovery failed" in err for err in snap_ps.errors)
    assert snap_ps.completeness in (DiscoveryCompleteness.PARTIAL, DiscoveryCompleteness.FAILED, DiscoveryCompleteness.DEGRADED)

    # 2. S3 list_objects failure
    s3_strat = S3DiscoveryStrategy()
    s3_conn = MagicMock()
    s3_conn.list_buckets.return_value = {"Buckets": [{"Name": "mybucket"}]}
    s3_conn.list_objects_v2.side_effect = RuntimeError("S3 403 Access Denied")
    snap_s3 = DiscoveryPipelineExecutor.execute(s3_strat, s3_conn, _make_spec("s3"), ctx)
    assert any("pagination failed" in err or "S3 403" in err for err in snap_s3.errors)
    assert snap_s3.completeness in (DiscoveryCompleteness.PARTIAL, DiscoveryCompleteness.FAILED, DiscoveryCompleteness.DEGRADED)

    # 3. Redshift table query failure
    rs_strat = RedshiftDiscoveryStrategy()
    rs_conn = MagicMock()
    rs_cur = MagicMock()
    rs_conn.cursor.return_value.__enter__.return_value = rs_cur
    rs_cur.fetchall.side_effect = [
        [("public",)],  # namespaces
        RuntimeError("Connection terminated unexpectedly"),  # tables query
    ]
    snap_rs = DiscoveryPipelineExecutor.execute(rs_strat, rs_conn, _make_spec("redshift"), ctx)
    assert any("pagination failed" in err or "Connection terminated" in err for err in snap_rs.errors)
    assert snap_rs.completeness in (DiscoveryCompleteness.PARTIAL, DiscoveryCompleteness.FAILED, DiscoveryCompleteness.DEGRADED)


def test_multi_provider_bulk_spi_implementations():
    """Verify MySQL, Oracle, MSSQL, Snowflake, and Cassandra bulk SPI implementations."""
    ctx = DiscoveryContext(depth=DiscoveryDepth.STANDARD)
    tbl_names = ["t1", "t2"]

    # MySQL bulk
    mysql_strat = MySQLDiscoveryStrategy()
    mysql_conn = MagicMock()
    mysql_cur = MagicMock()
    mysql_conn.cursor.return_value = mysql_cur
    mysql_cur.fetchall.side_effect = [
        [("t1", 1, "id", "int", 11, 10, 0, "NO", None, "auto_increment"), ("t2", 1, "code", "varchar", 50, 0, 0, "YES", None, "")],
        [("t1", "PRIMARY", "id", 0, "BTREE")],
    ]
    mysql_bulk = mysql_strat.discover_objects_structure_bulk(mysql_conn, _make_spec("mysql"), "mydb", tbl_names, ctx)
    assert len(mysql_bulk) == 2
    assert mysql_bulk["t1"].primary_key is not None

    # Snowflake bulk
    sf_strat = SnowflakeDiscoveryStrategy()
    sf_conn = MagicMock()
    sf_cur = MagicMock()
    sf_conn.cursor.return_value = sf_cur
    sf_cur.fetchall.return_value = [
        ("T1", 1, "ID", "NUMBER", None, 38, 0, "NO", None),
        ("T2", 1, "VAL", "VARCHAR", 100, None, None, "YES", None),
    ]
    sf_bulk = sf_strat.discover_objects_structure_bulk(sf_conn, _make_spec("snowflake"), "PUBLIC", ["T1", "T2"], ctx)
    assert len(sf_bulk) == 2
    assert len(sf_bulk["T1"].columns) == 1

    # Cassandra bulk
    cas_strat = CassandraDiscoveryStrategy()
    cas_conn = MagicMock()
    RowCol = MagicMock
    cas_conn.execute.side_effect = [
        [MagicMock(table_name="t1", column_name="id", type="uuid", kind="partition_key", position=0),
         MagicMock(table_name="t2", column_name="name", type="text", kind="regular", position=0)],
        [],
    ]
    cas_bulk = cas_strat.discover_objects_structure_bulk(cas_conn, _make_spec("cassandra"), "myks", tbl_names, ctx)
    assert len(cas_bulk) == 2
    assert cas_bulk["t1"].primary_key is not None


def test_relational_server_side_pagination_sql():
    """Verify that relational strategies emit server-side pagination SQL to avoid client-side full fetch."""
    ctx = DiscoveryContext()

    # 1. MySQL LIMIT / OFFSET
    mysql_strat = MySQLDiscoveryStrategy()
    mysql_conn = MagicMock()
    mysql_cur = MagicMock()
    mysql_conn.cursor.return_value = mysql_cur
    mysql_cur.fetchall.return_value = [("t1", "BASE TABLE", 100, 1024, 512)]
    page_mysql = mysql_strat.discover_objects_page(mysql_conn, _make_spec("mysql"), "mydb", ctx, page_size=200)
    assert "LIMIT %s OFFSET %s" in mysql_cur.execute.call_args[0][0]
    assert mysql_cur.execute.call_args[0][1] == ("mydb", 201, 0)
    assert len(page_mysql.items) == 1

    # 2. MSSQL OFFSET / FETCH NEXT
    mssql_strat = MSSQLDiscoveryStrategy()
    mssql_conn = MagicMock()
    mssql_cur = MagicMock()
    mssql_conn.cursor.return_value = mssql_cur
    mssql_cur.fetchall.side_effect = [[], [("t1", "U", 500)]]  # views, then tables
    page_mssql = mssql_strat.discover_objects_page(mssql_conn, _make_spec("mssql"), "dbo", ctx, page_size=100)
    assert "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY" in mssql_cur.execute.call_args_list[1][0][0]
    assert mssql_cur.execute.call_args_list[1][0][1] == ("dbo", 0, 101)

    # 3. Oracle OFFSET / FETCH NEXT
    oracle_strat = OracleDiscoveryStrategy()
    oracle_conn = MagicMock()
    oracle_cur = MagicMock()
    oracle_conn.cursor.return_value.__enter__.return_value = oracle_cur
    oracle_cur.fetchall.return_value = [("T1", 1000, 50, None, "N")]
    page_ora = oracle_strat.discover_objects_page(oracle_conn, _make_spec("oracle"), "HR", ctx, page_size=50)
    assert "OFFSET :2 ROWS FETCH NEXT :3 ROWS ONLY" in oracle_cur.execute.call_args[0][0]
    assert oracle_cur.execute.call_args[0][1] == ["HR", 0, 51]

    # 4. IBM DB2 LIMIT / OFFSET
    from akaalEngine.discovery.strategies.relational.ibm_db2 import IBMDb2DiscoveryStrategy
    db2_strat = IBMDb2DiscoveryStrategy()
    db2_conn = MagicMock()
    db2_cur = MagicMock()
    db2_conn.cursor.return_value = db2_cur
    db2_cur.fetchall.return_value = [("T1", "T", 500, 10)]
    page_db2 = db2_strat.discover_objects_page(db2_conn, _make_spec("ibm_db2"), "DB2INST1", ctx, page_size=100)
    assert "LIMIT ? OFFSET ?" in db2_cur.execute.call_args[0][0]
    assert db2_cur.execute.call_args[0][1] == ("DB2INST1", 101, 0)

    # 5. Snowflake LIMIT / OFFSET
    sf_strat = SnowflakeDiscoveryStrategy()
    sf_conn = MagicMock()
    sf_cur = MagicMock()
    sf_conn.cursor.return_value = sf_cur
    sf_cur.fetchall.return_value = [("T1", "BASE TABLE", 200, 8192)]
    page_sf = sf_strat.discover_objects_page(sf_conn, _make_spec("snowflake"), "PUBLIC", ctx, page_size=500)
    assert "LIMIT %s OFFSET %s" in sf_cur.execute.call_args[0][0]
    assert sf_cur.execute.call_args[0][1] == ("PUBLIC", 501, 0)


def test_physical_failure_re_raised_not_suppressed():
    """Physical discovery failures are re-raised and never suppressed into fake empty results."""
    ctx = DiscoveryContext()

    # 1. Postgres structure query failure
    pg_strat = PostgresDiscoveryStrategy()
    pg_conn = MagicMock()
    pg_cur = MagicMock()
    pg_conn.cursor.return_value.__enter__.return_value = pg_cur
    pg_cur.execute.side_effect = RuntimeError("relation not found or lock timeout")
    with pytest.raises(RuntimeError, match="lock timeout"):
        pg_strat.discover_object_structure(pg_conn, _make_spec("postgresql"), "public", "users", ctx)

    # 2. Postgres bulk structure failure
    with pytest.raises(RuntimeError, match="lock timeout"):
        pg_strat.discover_objects_structure_bulk(pg_conn, _make_spec("postgresql"), "public", ["users"], ctx)

    # 3. MySQL structure query failure
    my_strat = MySQLDiscoveryStrategy()
    my_conn = MagicMock()
    my_cur = MagicMock()
    my_conn.cursor.return_value = my_cur
    my_cur.execute.side_effect = RuntimeError("Lost connection to MySQL server")
    with pytest.raises(RuntimeError, match="Lost connection"):
        my_strat.discover_object_structure(my_conn, _make_spec("mysql"), "mydb", "orders", ctx)

    # 4. BigQuery table stats query failure
    bq_strat = BigQueryDiscoveryStrategy()
    bq_conn = MagicMock()
    bq_conn.get_table.side_effect = RuntimeError("BigQuery 503 Backend Error")
    with pytest.raises(RuntimeError, match="503 Backend Error"):
        bq_strat.discover_table_statistics(bq_conn, _make_spec("bigquery"), "dataset", "events", ctx)

    # 5. Cassandra structure query failure
    cas_strat = CassandraDiscoveryStrategy()
    cas_conn = MagicMock()
    cas_conn.execute.side_effect = RuntimeError("Cassandra read timeout or host unavailable")
    with pytest.raises(RuntimeError, match="Cassandra read timeout"):
        cas_strat.discover_object_structure(cas_conn, _make_spec("cassandra"), "myks", "mytbl", ctx)

    # 6. Cassandra bulk structure query failure
    with pytest.raises(RuntimeError, match="Cassandra read timeout"):
        cas_strat.discover_objects_structure_bulk(cas_conn, _make_spec("cassandra"), "myks", ["mytbl"], ctx)

    # 7. Elasticsearch mapping query failure
    es_strat = ElasticsearchDiscoveryStrategy()
    es_conn = MagicMock()
    es_conn.indices.get_mapping.side_effect = RuntimeError("Elasticsearch cluster unavailable")
    with pytest.raises(RuntimeError, match="cluster unavailable"):
        es_strat.discover_object_structure(es_conn, _make_spec("elasticsearch"), "default", "myindex", ctx)


def test_enforced_operation_timeout_causes_partial_snapshot():
    """When discovery deadline expires, executor stops gracefully, marks timeout, and returns partial snapshot."""
    ctx = DiscoveryContext(timeout_seconds=0.001)  # tiny deadline that expires immediately
    strat = PostgresDiscoveryStrategy()
    strat.discover_namespaces = MagicMock(return_value=NamespaceInventory(schemas=("public",)))
    strat.discover_objects_page = MagicMock(return_value=ObjectInventoryPage(items=(TableFacts(name="t1", schema_name="public"),)))
    
    mock_conn = MagicMock()
    # Artificially delay so time > deadline
    import time
    time.sleep(0.005)

    snap = DiscoveryPipelineExecutor.execute(strat, mock_conn, _make_spec("postgresql"), ctx)
    assert any("deadline" in w or "timed out" in w for w in snap.warnings)
    assert snap.completeness in (DiscoveryCompleteness.PARTIAL, DiscoveryCompleteness.DEGRADED, DiscoveryCompleteness.FAILED)


def test_blocking_provider_operation_bounded_by_executor_timeout():
    """A blocking SQL/SDK operation (simulated with sleep) is strictly bounded by the executor timeout and does not hang indefinitely."""
    import time
    ctx = DiscoveryContext(timeout_seconds=0.1)  # 100ms timeout
    strat = PostgresDiscoveryStrategy()

    def blocking_namespaces(conn, spec, ctx):
        time.sleep(5.0)  # Blocking call that would hang 5 seconds
        return NamespaceInventory(schemas=("public",))

    strat.discover_namespaces = blocking_namespaces
    mock_conn = MagicMock()

    t_start = time.time()
    snap = DiscoveryPipelineExecutor.execute(strat, mock_conn, _make_spec("postgresql"), ctx)
    elapsed = time.time() - t_start

    # Must finish within < 1.0 second rather than hanging for 5.0 seconds!
    assert elapsed < 1.0
    assert any("timed out" in w or "deadline" in w for w in snap.warnings)
    assert snap.completeness in (DiscoveryCompleteness.PARTIAL, DiscoveryCompleteness.DEGRADED, DiscoveryCompleteness.FAILED)


def test_timed_out_session_quarantined_and_invalidated():
    """When a provider operation times out, the session lease is poisoned, closed, and invalidated rather than reused."""
    import time
    from akaalEngine.discovery.authority import DiscoveryAuthority
    from akaalEngine.discovery.core.coordinator import DiscoverySessionCoordinator
    from akaalEngine.connection.models.session import InternalSessionHandle, SessionLease, SessionPurpose, IsolationLevel

    mock_conn = MagicMock()
    handle = InternalSessionHandle(
        session_id="test-sess-1",
        fingerprint="fp1",
        purpose=SessionPurpose.DISCOVERY,
        provider_id="sqlite",
        physical_connection=mock_conn,
    )
    lease = SessionLease(
        lease_id="lease-1",
        session_id="test-sess-1",
        purpose=SessionPurpose.DISCOVERY,
        endpoint_fingerprint="fp1",
        provider_id="sqlite",
        isolation_level=IsolationLevel.READ_COMMITTED,
        is_read_only=True,
        borrower_id="DiscoveryAuthority",
        created_at="2026-08-22T00:00:00Z",
        _internal_handle=handle,
    )

    mock_conn_auth = MagicMock()
    mock_ext_auth = MagicMock()
    coordinator = DiscoverySessionCoordinator(
        connection_authority=mock_conn_auth,
        extensions_authority=mock_ext_auth,
    )

    # 1. Direct invalidation of timed-out session
    coordinator.invalidate_discovery_session(lease)
    assert handle.is_poisoned is True
    assert handle.is_closed is True
    mock_conn.close.assert_called()
    mock_conn_auth.invalidate_session.assert_called_with(lease)

    # 2. Release with is_timed_out=True triggers quarantine/invalidation
    handle.is_poisoned = False
    handle.is_closed = False
    mock_conn.reset_mock()
    mock_conn_auth.reset_mock()
    coordinator.release_discovery_session(lease, is_timed_out=True)
    assert handle.is_poisoned is True
    assert handle.is_closed is True
    mock_conn.close.assert_called()
    mock_conn_auth.invalidate_session.assert_called_with(lease)




