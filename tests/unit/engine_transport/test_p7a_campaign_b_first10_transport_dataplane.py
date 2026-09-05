"""
tests.unit.engine_transport.test_p7a_campaign_b_first10_transport_dataplane
================================================================================
P7A Campaign B — First-10-Provider canonical physical data-plane proof.

Proves the previously-missing "Engine -> actual physical extraction/write" path is now
real production code, for all 10 first-Campaign-B providers, by exercising the REAL
SourceReader/TargetWriter classes registered in
`akaalEngine.transport.drivers.registry.default_transport_driver_registry` end to end.

Mocks exist ONLY at the final external SDK/client boundary (a fake pika channel, a fake
pulsar client/consumer/producer, a fake boto3 dynamodb client, a fake couchbase cluster, a
fake clickhouse_connect client, a fake influxdb_client connection, a fake DB-API 2.0
cursor/connection for the SQL-wire-compatible providers). Every layer above that boundary
(SourceReader.open_partition/read_batch, TargetWriter.write_batch/commit,
TransportAuthority.execute_partition_transport, TransportCheckpoint identity) is real,
unmodified-for-testing production code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.drivers.registry import default_transport_driver_registry
from akaalEngine.transport.models.capabilities import CommitOutcomeState, IdempotencyMode, ResumabilityMode
from akaalEngine.transport.models.checkpoint import TransportCheckpoint
from akaalEngine.transport.models.errors import TransportCheckpointIdentityError, TransportCheckpointStaleError
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition


def _partition(table_name="t1", schema_name="s1", target_schema="s1", partition_id="p0", pk_columns=()):
    return TransportPartition(
        partition_id=partition_id,
        table_name=table_name,
        schema_name=schema_name,
        target_schema=target_schema,
        strategy=PartitionStrategy.SINGLE_PARTITION,
        pk_columns=tuple(pk_columns),
    )


# ---------------------------------------------------------------------------
# 1. Registry resolution proves reachability for all 10 providers
# ---------------------------------------------------------------------------

NEW_PROVIDERS = [
    "cockroachdb", "rabbitmq", "pulsar", "dynamodb", "couchbase",
    "clickhouse", "influxdb", "yugabytedb", "tidb", "singlestore",
]


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_transport_authority_resolves_real_reader_and_writer(provider_id):
    """Every one of the 10 providers must resolve a REAL, distinct SourceReader/TargetWriter
    class through TransportAuthority -- proving 'Engine -> physical data plane' is reachable,
    not merely 'Engine -> connect() -> native client object' as before this hardening pass."""
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={})
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={})
    assert reader is not None
    assert writer is not None
    assert reader.get_capabilities() is not None
    assert writer.get_capabilities() is not None


def test_unregistered_provider_fails_closed_not_silently():
    ta = TransportAuthority()
    from akaalEngine.transport.models.errors import TransportCapabilityError
    with pytest.raises(TransportCapabilityError):
        ta.resolve_source_reader_for_provider("totally-unknown-provider-xyz")


# ---------------------------------------------------------------------------
# 2. CockroachDB / YugabyteDB — real DB-API cursor + psycopg2-shaped write boundary
# ---------------------------------------------------------------------------

class _FakeSqlCursor:
    def __init__(self, rows, description):
        self._rows = list(rows)
        self.description = description
        self.rowcount = -1
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def executemany(self, sql, seq_of_params):
        self.executed.append((sql, seq_of_params))
        self.rowcount = len(seq_of_params)

    def fetchmany(self, n):
        batch, self._rows = self._rows[:n], self._rows[n:]
        return batch

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def close(self):
        pass


class _FakeSqlConnection:
    __module__ = "psycopg2.extensions"  # drives paramstyle resolution to 'pyformat'

    def __init__(self, rows, description):
        self._cursor = _FakeSqlCursor(rows, description)
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_cockroachdb_reader_reaches_real_cursor_and_bounds_batches():
    """GenericSQLSourceReader (real, shared, paramstyle-aware) must actually call
    cursor.execute()/fetchmany() with the CockroachDB partition's real table/schema/pk,
    and must stop after two bounded fetchmany() calls rather than materializing everything."""
    rows = [(i, f"name{i}") for i in range(7)]
    conn = _FakeSqlConnection(rows, description=[("id",), ("name",)])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("cockroachdb", connection_params={"db_connection": conn})

    reader.open_partition(_partition(table_name="orders", schema_name="public", pk_columns=("id",)))
    assert conn._cursor.executed, "reader must have issued a real SELECT against the fake cursor"
    assert "orders" in conn._cursor.executed[0][0]

    b1 = reader.read_batch(batch_size=5)
    assert b1 is not None and len(b1.rows) == 5
    b2 = reader.read_batch(batch_size=5)
    assert b2 is not None and len(b2.rows) == 2
    b3 = reader.read_batch(batch_size=5)
    assert b3 is None  # bounded EOF, not an unbounded materialization


def test_cockroachdb_writer_reaches_real_psycopg2_execute_values_boundary(monkeypatch):
    """CockroachDBTargetWriter must call the REAL psycopg2.extras.execute_values entrypoint
    (patched only at that external-library boundary) with CockroachDB's own connection
    identity (distinct class from PostgreSQLTargetWriter)."""
    from akaalEngine.transport.drivers.cockroachdb import CockroachDBTargetWriter
    import akaalEngine.transport.drivers.postgres as postgres_mod

    fake_conn = MagicMock()
    fake_cursor = MagicMock()
    fake_cursor.rowcount = 3
    fake_conn.cursor.return_value = fake_cursor

    calls = {}

    def fake_execute_values(cursor, sql, data):
        calls["sql"] = sql
        calls["data"] = data

    monkeypatch.setattr(postgres_mod.psycopg2, "connect", lambda **kw: fake_conn)
    monkeypatch.setattr(postgres_mod.psycopg2.extras, "execute_values", fake_execute_values)

    writer = CockroachDBTargetWriter({"host": "crdb.internal", "user": "root", "dbname": "defaultdb"})
    assert type(writer).__name__ == "CockroachDBTargetWriter"

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="public", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )
    written = writer.write_batch("orders", batch, target_schema="public", pk_columns=["id"])
    assert written == 3
    assert "orders" in calls["sql"]
    writer.commit()
    assert fake_conn.commit.called


# ---------------------------------------------------------------------------
# 3. RabbitMQ — real pika basic_get/basic_publish boundary, deferred ack semantics
# ---------------------------------------------------------------------------

class _FakeMethod:
    def __init__(self, routing_key, delivery_tag, redelivered=False):
        self.routing_key = routing_key
        self.delivery_tag = delivery_tag
        self.redelivered = redelivered


class _FakeProps:
    content_type = "application/json"
    headers = {}


class _FakeRabbitChannel:
    def __init__(self, messages):
        self._messages = list(messages)  # list of (routing_key, body)
        self._next_tag = 1
        self.acked_tags: List[int] = []
        self.published: List[Dict[str, Any]] = []
        self._confirm_delivery_enabled = False
        self.closed = False

    def basic_qos(self, prefetch_count):
        pass

    def basic_get(self, queue, auto_ack=False):
        if not self._messages:
            return None, None, None
        rk, body = self._messages.pop(0)
        tag = self._next_tag
        self._next_tag += 1
        return _FakeMethod(rk, tag), _FakeProps(), body

    def basic_ack(self, delivery_tag):
        self.acked_tags.append(delivery_tag)

    def confirm_delivery(self):
        self._confirm_delivery_enabled = True

    def basic_publish(self, exchange, routing_key, body, mandatory=False):
        self.published.append({"exchange": exchange, "routing_key": routing_key, "body": body})
        return True

    def close(self):
        self.closed = True


class _FakeRabbitConnection:
    def __init__(self, channel):
        self._channel = channel

    def channel(self):
        return self._channel


def test_rabbitmq_reader_reaches_real_basic_get_and_defers_ack():
    channel = _FakeRabbitChannel([("rk1", b"hello"), ("rk1", b"world")])
    conn = _FakeRabbitConnection(channel)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("rabbitmq", connection_params={"db_connection": conn})

    reader.open_partition(_partition(table_name="orders.q"))
    batch = reader.read_batch(batch_size=10)
    assert batch is not None
    assert len(batch.rows) == 2
    assert batch.rows[0]["body"] == b"hello"
    # Deferred-ack contract: nothing acked yet after the FIRST read_batch (see driver docstring).
    assert channel.acked_tags == []

    # A second read_batch (EOF) must ack the PRIOR batch's delivery tags before returning None.
    next_batch = reader.read_batch(batch_size=10)
    assert next_batch is None
    assert channel.acked_tags == [1, 2]

    reader.close()
    # close() must NOT ack anything further (nothing pending here, but proves no forced-ack-on-close).
    assert channel.acked_tags == [1, 2]


def test_rabbitmq_writer_reaches_real_basic_publish_with_confirms():
    channel = _FakeRabbitChannel([])
    conn = _FakeRabbitConnection(channel)
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("rabbitmq", connection_params={"db_connection": conn})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders.q", schema_name="/", sequence_number=1, row_count=1, size_bytes=5),
        rows=[{"body": b"payload", "routing_key": "orders.q"}],
        column_names=["body", "routing_key"],
    )
    written = writer.write_batch("orders.q", batch, target_schema="")
    assert written == 1
    assert channel.published[0]["body"] == b"payload"
    assert channel._confirm_delivery_enabled is True

    with pytest.raises(Exception):
        writer.rollback()  # RabbitMQ cannot un-publish -- must fail truthfully, not silently no-op


# ---------------------------------------------------------------------------
# 4. DynamoDB — real boto3 scan()/batch_write_item() boundary, LastEvaluatedKey pagination
# ---------------------------------------------------------------------------

class _FakeDynamoClient:
    def __init__(self, pages):
        self._pages = list(pages)  # list of (items, last_evaluated_key)
        self.scan_calls: List[Dict[str, Any]] = []
        self.batch_write_calls: List[Dict[str, Any]] = []
        self.get_item_calls: List[Dict[str, Any]] = []

    def scan(self, **kwargs):
        self.scan_calls.append(kwargs)
        items, lek = self._pages.pop(0)
        resp = {"Items": items}
        if lek:
            resp["LastEvaluatedKey"] = lek
        return resp

    def batch_write_item(self, RequestItems):
        self.batch_write_calls.append(RequestItems)
        return {"UnprocessedItems": {}}

    def get_item(self, TableName, Key):
        self.get_item_calls.append({"TableName": TableName, "Key": Key})
        return {"Item": {"id": {"S": "1"}}}


def test_dynamodb_reader_reaches_real_scan_and_bounds_via_last_evaluated_key():
    page1_items = [{"id": {"S": "1"}}, {"id": {"S": "2"}}]
    page2_items = [{"id": {"S": "3"}}]
    client = _FakeDynamoClient([
        (page1_items, {"id": {"S": "2"}}),
        (page2_items, None),
    ])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("dynamodb", connection_params={"db_connection": client})

    reader.open_partition(_partition(table_name="Orders"))
    b1 = reader.read_batch(batch_size=5)
    assert b1 is not None and len(b1.rows) == 2
    assert client.scan_calls[0]["TableName"] == "Orders"
    assert "ExclusiveStartKey" not in client.scan_calls[0]

    b2 = reader.read_batch(batch_size=5)
    assert b2 is not None and len(b2.rows) == 1
    assert client.scan_calls[1]["ExclusiveStartKey"] == {"id": {"S": "2"}}  # real continuation, not offset

    b3 = reader.read_batch(batch_size=5)
    assert b3 is None


def test_dynamodb_writer_reaches_real_batch_write_item_and_respects_25_item_limit():
    client = _FakeDynamoClient([])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("dynamodb", connection_params={"db_connection": client})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    rows = [{"id": str(i), "value": i} for i in range(30)]  # exceeds the 25-item BatchWriteItem limit
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="Orders", schema_name="", sequence_number=1, row_count=30, size_bytes=100),
        rows=rows,
        column_names=["id", "value"],
    )
    written = writer.write_batch("Orders", batch, pk_columns=["id"])
    assert written == 30
    assert len(client.batch_write_calls) == 2  # chunked into <=25-item requests, not one oversized call
    assert len(client.batch_write_calls[0]["Orders"]) == 25
    assert len(client.batch_write_calls[1]["Orders"]) == 5

    outcome = writer.verify_uncertain_commit("Orders", "", ["id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    assert client.get_item_calls  # real physical GetItem verification, not a fabricated guess


# ---------------------------------------------------------------------------
# 5. ClickHouse — real clickhouse_connect query()/insert() boundary
# ---------------------------------------------------------------------------

class _FakeCHResult:
    def __init__(self, rows, column_names):
        self.result_rows = rows
        self.column_names = column_names


class _FakeClickHouseClient:
    def __init__(self, pages):
        self._pages = list(pages)
        self.queries: List[str] = []
        self.inserts: List[Dict[str, Any]] = []

    def query(self, sql):
        self.queries.append(sql)
        rows, cols = self._pages.pop(0)
        return _FakeCHResult(rows, cols)

    def insert(self, table, data, column_names, database):
        self.inserts.append({"table": table, "data": data, "column_names": column_names, "database": database})


def test_clickhouse_reader_reaches_real_query_with_offset_pagination():
    client = _FakeClickHouseClient([
        ([(1, "a"), (2, "b")], ["id", "name"]),
        ([], ["id", "name"]),
    ])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("clickhouse", connection_params={"db_connection": client})
    reader.open_partition(_partition(table_name="events", schema_name="analytics"))

    b1 = reader.read_batch(batch_size=5)
    assert b1 is not None and len(b1.rows) == 2
    assert "OFFSET 0" in client.queries[0]
    assert "analytics" in client.queries[0] and "events" in client.queries[0]


def test_clickhouse_writer_reaches_real_insert_and_cannot_rollback():
    client = _FakeClickHouseClient([])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("clickhouse", connection_params={"db_connection": client})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="events", schema_name="analytics", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )
    written = writer.write_batch("events", batch, target_schema="analytics")
    assert written == 1
    assert client.inserts[0]["table"] == "events"
    writer.commit()  # must be a safe no-op, not an error
    with pytest.raises(Exception):
        writer.rollback()  # ClickHouse has no transaction to undo -- must fail truthfully


# ---------------------------------------------------------------------------
# 6. Checkpoint identity — wrong-provider / wrong-resource rejection (generic, shared model)
# ---------------------------------------------------------------------------

def test_transport_checkpoint_rejects_wrong_resource_identity():
    original = TransportCheckpoint(
        source_identity="cockroachdb://cluster-a",
        source_resource_version="v1",
        target_identity="dynamodb://table-orders",
        logical_object_name="orders",
        schema_fingerprint="fp-orders-v1",
        partition_id="p0",
        partition_strategy_fingerprint="single",
        processing_plan_fingerprint="plan-1",
        transport_strategy_identity="cockroachdb->dynamodb",
    )
    wrong_resource = TransportCheckpoint(
        source_identity="cockroachdb://cluster-a",
        source_resource_version="v1",
        target_identity="dynamodb://table-orders",
        logical_object_name="customers",  # different logical resource
        schema_fingerprint="fp-orders-v1",
        partition_id="p0",
        partition_strategy_fingerprint="single",
        processing_plan_fingerprint="plan-1",
        transport_strategy_identity="cockroachdb->dynamodb",
    )
    with pytest.raises(TransportCheckpointIdentityError):
        wrong_resource.validate_compatibility(original)


def test_transport_checkpoint_rejects_stale_generation():
    base_kwargs = dict(
        source_identity="rabbitmq://vhost-a",
        source_resource_version="v1",
        target_identity="pulsar://tenant-a",
        logical_object_name="orders.q",
        schema_fingerprint="fp-1",
        partition_id="p0",
        partition_strategy_fingerprint="single",
        processing_plan_fingerprint="plan-1",
        transport_strategy_identity="rabbitmq->pulsar",
    )
    newer = TransportCheckpoint(**base_kwargs, generation=3)
    stale = TransportCheckpoint(**base_kwargs, generation=1)
    with pytest.raises(TransportCheckpointStaleError):
        stale.validate_compatibility(newer)


# ---------------------------------------------------------------------------
# 7. Idempotency classification truth — not merely documented
# ---------------------------------------------------------------------------

def test_write_idempotency_classifications_match_real_provider_semantics():
    """DynamoDB/InfluxDB/Couchbase writers overwrite-by-key and are genuinely
    OPERATION_IDEMPOTENT; RabbitMQ/Pulsar publish and ClickHouse insert are NOT --
    a replayed publish/insert is a genuine duplicate, so retry must not silently assume safety."""
    ta = TransportAuthority()

    assert ta.resolve_target_writer_for_provider("dynamodb", connection_params={}).get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    assert ta.resolve_target_writer_for_provider("couchbase", connection_params={}).get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    assert ta.resolve_target_writer_for_provider("influxdb", connection_params={}).get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    assert ta.resolve_target_writer_for_provider("clickhouse", connection_params={}).get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT
    assert ta.resolve_target_writer_for_provider("rabbitmq", connection_params={}).get_capabilities().idempotency == IdempotencyMode.CONDITIONALLY_IDEMPOTENT
    assert ta.resolve_target_writer_for_provider("pulsar", connection_params={}).get_capabilities().idempotency == IdempotencyMode.CONDITIONALLY_IDEMPOTENT


# ---------------------------------------------------------------------------
# 8. Full canonical orchestrator reachability (TransportAuthority.execute_partition_transport)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 9. Couchbase — real N1QL query()/collection.upsert() boundary
# ---------------------------------------------------------------------------

class _FakeCouchbaseCollection:
    def __init__(self):
        self.upserts: Dict[str, Any] = {}
        self.gets: List[str] = []

    def upsert(self, doc_id, value):
        self.upserts[doc_id] = value

    def get(self, doc_id):
        self.gets.append(doc_id)
        if doc_id not in self.upserts:
            raise Exception("DocumentNotFoundException")
        return self.upserts[doc_id]


class _FakeCouchbaseScope:
    def __init__(self, collection):
        self._collection = collection

    def collection(self, name):
        return self._collection


class _FakeCouchbaseBucket:
    def __init__(self, scope):
        self._scope = scope

    def scope(self, name):
        return self._scope


class _FakeCouchbaseCluster:
    def __init__(self, query_pages, collection):
        self._pages = list(query_pages)
        self._collection = collection
        self.queries: List[str] = []

    def query(self, n1ql):
        self.queries.append(n1ql)
        return iter(self._pages.pop(0))

    def bucket(self, name):
        return _FakeCouchbaseBucket(_FakeCouchbaseScope(self._collection))


def test_couchbase_reader_reaches_real_n1ql_query_with_offset_pagination():
    collection = _FakeCouchbaseCollection()
    cluster = _FakeCouchbaseCluster([[{"__doc_id": "d1", "name": "a"}], []], collection)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("couchbase", connection_params={"db_connection": cluster, "bucket": "b1"})
    reader.open_partition(_partition(table_name="orders", schema_name="_default.orders"))

    b1 = reader.read_batch(batch_size=5)
    assert b1 is not None and len(b1.rows) == 1
    assert "b1" in cluster.queries[0] and "orders" in cluster.queries[0]
    assert "OFFSET 0" in cluster.queries[0]


def test_couchbase_writer_reaches_real_upsert_and_verify_uncertain_commit():
    collection = _FakeCouchbaseCollection()
    cluster = _FakeCouchbaseCluster([], collection)
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("couchbase", connection_params={"db_connection": cluster, "bucket": "b1"})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"__doc_id": "order-1", "amount": 42}],
        column_names=["__doc_id", "amount"],
    )
    written = writer.write_batch("orders", batch, target_schema="_default.orders")
    assert written == 1
    assert collection.upserts["order-1"] == {"amount": 42}

    outcome = writer.verify_uncertain_commit("orders", "_default.orders", [], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    with pytest.raises(Exception):
        writer.rollback()


# ---------------------------------------------------------------------------
# 10. InfluxDB — real Flux query_api()/write_api() boundary
# ---------------------------------------------------------------------------

class _FakeInfluxRecord:
    def __init__(self, time_val, field, value, tags):
        self._time = time_val
        self._field = field
        self._value = value
        self.values = {"_time": time_val, "_field": field, "_value": value, **tags}

    def get_time(self):
        return self._time

    def get_field(self):
        return self._field

    def get_value(self):
        return self._value


class _FakeInfluxTable:
    def __init__(self, records):
        self.records = records


class _FakeInfluxQueryApi:
    def __init__(self, pages):
        self._pages = list(pages)
        self.fluxes: List[str] = []

    def query(self, flux, org):
        self.fluxes.append(flux)
        return self._pages.pop(0)


class _FakeInfluxWriteApi:
    def __init__(self):
        self.written = []

    def write(self, bucket, org, record):
        self.written.append({"bucket": bucket, "org": org, "record": record})


class _FakeInfluxClient:
    def __init__(self, query_pages):
        self._query_api = _FakeInfluxQueryApi(query_pages)
        self._write_api = _FakeInfluxWriteApi()

    def query_api(self):
        return self._query_api

    def write_api(self):
        return self._write_api


def test_influxdb_reader_reaches_real_flux_query_with_time_range_pagination():
    import datetime
    t1 = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2024, 1, 2, tzinfo=datetime.timezone.utc)
    # A FULL batch_size=1 page each time (not fewer-than-requested) so the reader does not
    # yet treat this as end-of-stream -- isolates proving the range boundary genuinely
    # advances between calls from the separate (and separately correct) early-EOF heuristic.
    page1 = [_FakeInfluxTable([_FakeInfluxRecord(t1, "temp", 21.5, {"host": "srv1"})])]
    page2 = [_FakeInfluxTable([_FakeInfluxRecord(t2, "temp", 22.0, {"host": "srv1"})])]
    page3 = [_FakeInfluxTable([])]
    client = _FakeInfluxClient([page1, page2, page3])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("influxdb", connection_params={"db_connection": client, "org": "myorg"})
    reader.open_partition(_partition(table_name="cpu", schema_name="metrics"))

    b1 = reader.read_batch(batch_size=1)
    assert b1 is not None and len(b1.rows) == 1
    assert "metrics" in client._query_api.fluxes[0] and "cpu" in client._query_api.fluxes[0]
    assert "range(start: 1970-01-01T00:00:00Z)" in client._query_api.fluxes[0]

    # Range boundary must have advanced past the last-seen timestamp for the NEXT call.
    b2 = reader.read_batch(batch_size=1)
    assert b2 is not None and len(b2.rows) == 1
    assert "1970-01-01T00:00:00Z" not in client._query_api.fluxes[1]

    b3 = reader.read_batch(batch_size=1)
    assert b3 is None  # genuine empty page -> real end-of-stream


class _FakePoint:
    """Mirrors the real influxdb_client.Point builder API shape (chainable .tag()/.field()/
    .time()) closely enough to prove the production writer distinguishes tags from fields --
    used only because `influxdb_client` is not installed in this environment; the writer's
    own production code path (constructing and populating a Point) is exercised for real."""

    def __init__(self, measurement):
        self.measurement = measurement
        self._tags: Dict[str, str] = {}
        self._fields: Dict[str, Any] = {}
        self._time = None

    def tag(self, k, v):
        self._tags[k] = v
        return self

    def field(self, k, v):
        self._fields[k] = v
        return self

    def time(self, t):
        self._time = t
        return self


def test_influxdb_writer_reaches_real_write_api_with_tag_field_distinction(monkeypatch):
    import sys
    import types
    fake_module = types.ModuleType("influxdb_client")
    fake_module.Point = _FakePoint
    monkeypatch.setitem(sys.modules, "influxdb_client", fake_module)

    client = _FakeInfluxClient([])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("influxdb", connection_params={"db_connection": client, "org": "myorg"})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="cpu", schema_name="metrics", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"host": "srv1", "usage": 55.2}],
        column_names=["host", "usage"],
    )
    written = writer.write_batch("cpu", batch, target_schema="metrics", pk_columns=["host"])
    assert written == 1
    assert client._write_api.written[0]["bucket"] == "metrics"
    point = client._write_api.written[0]["record"][0]
    # A tag key (host) must be a genuine Point tag, not flattened into a field.
    assert point._tags.get("host") == "srv1"
    assert "usage" in point._fields


# ---------------------------------------------------------------------------
# 11. Pulsar — real consumer.receive()/producer.send() boundary
# ---------------------------------------------------------------------------

class _FakePulsarMessage:
    def __init__(self, mid, data):
        self._mid = mid
        self._data = data

    def message_id(self):
        return self._mid

    def data(self):
        return self._data

    def properties(self):
        return {}

    def publish_timestamp(self):
        return 0

    def partition_key(self):
        return None


class _FakePulsarConsumer:
    def __init__(self, messages):
        self._messages = list(messages)
        self.acked_ids: List[str] = []
        self.closed = False

    def receive(self, timeout_millis=2000):
        if not self._messages:
            raise Exception("TimeoutError")
        return self._messages.pop(0)

    def acknowledge_cumulative(self, msg):
        self.acked_ids.append(msg.message_id())

    def close(self):
        self.closed = True


class _FakePulsarProducer:
    def __init__(self):
        self.sent: List[Dict[str, Any]] = []

    def send(self, data, properties=None, partition_key=None):
        self.sent.append({"data": data, "properties": properties, "partition_key": partition_key})

    def close(self):
        pass


class _FakePulsarClient:
    def __init__(self, consumer=None):
        self._consumer = consumer
        self._producer = _FakePulsarProducer()
        self.subscribed: List[Any] = []

    def subscribe(self, topic, subscription):
        self.subscribed.append((topic, subscription))
        return self._consumer

    def create_producer(self, topic):
        return self._producer


def test_pulsar_reader_reaches_real_consumer_receive_and_defers_cumulative_ack():
    consumer = _FakePulsarConsumer([_FakePulsarMessage("m1", b"hello"), _FakePulsarMessage("m2", b"world")])
    client = _FakePulsarClient(consumer=consumer)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("pulsar", connection_params={"db_connection": client})

    reader.open_partition(_partition(table_name="persistent://t/ns/orders"))
    assert client.subscribed  # real subscribe() reached

    b1 = reader.read_batch(batch_size=10)
    assert b1 is not None and len(b1.rows) == 2
    assert consumer.acked_ids == []  # deferred-ack, same rationale as RabbitMQ

    b2 = reader.read_batch(batch_size=10)
    assert b2 is None
    assert consumer.acked_ids == ["m2"]  # cumulative ack of the LAST message in the prior batch


def test_pulsar_writer_reaches_real_producer_send():
    client = _FakePulsarClient()
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("pulsar", connection_params={"db_connection": client})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="persistent://t/ns/orders", schema_name="", sequence_number=1, row_count=1, size_bytes=5),
        rows=[{"data": b"payload", "properties": {}, "partition_key": None}],
        column_names=["data", "properties", "partition_key"],
    )
    written = writer.write_batch("persistent://t/ns/orders", batch)
    assert written == 1
    assert client._producer.sent[0]["data"] == b"payload"
    with pytest.raises(Exception):
        writer.rollback()


# ---------------------------------------------------------------------------
# 12. TiDB / SingleStore — GenericSQL(Reader/Writer) is now genuinely correct for
#     MySQL-wire (pymysql, 'pyformat') connections, not just SQLite's '?' style.
# ---------------------------------------------------------------------------

class _FakeMySQLLikeConnection(_FakeSqlConnection):
    __module__ = "pymysql.connections"  # drives paramstyle resolution to 'pyformat'


@pytest.mark.parametrize("provider_id", ["tidb", "singlestore"])
def test_mysql_wire_compatible_writer_uses_correct_placeholder_style(provider_id):
    """Regression proof for the real defect found and fixed during this hardening pass:
    GenericSQLTargetWriter previously hardcoded '?' (qmark), which is invalid syntax for
    psycopg2/pymysql connections (both declare 'pyformat'). This proves TiDB/SingleStore's
    real target-write path now builds a correct '%s'-style INSERT statement."""
    conn = _FakeMySQLLikeConnection(rows=[], description=[])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn})

    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="s", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )
    writer.write_batch("orders", batch, target_schema="s")
    executed_sql = conn._cursor.executed[0][0]
    assert "%s" in executed_sql
    assert "?" not in executed_sql


def test_full_transport_authority_execution_reaches_dynamodb_physical_boundary():
    """End-to-end proof: TransportAuthority.execute_partition_transport() (the real,
    shared, canonical orchestrator -- same one used for SQL/file transport) drives a REAL
    DynamoDBSourceReader/DynamoDBTargetWriter all the way to the mocked boto3 client calls."""
    read_client = _FakeDynamoClient([([{"id": {"S": "1"}}, {"id": {"S": "2"}}], None)])
    write_client = _FakeDynamoClient([])

    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("dynamodb", connection_params={"db_connection": read_client})
    writer = ta.resolve_target_writer_for_provider("dynamodb", connection_params={"db_connection": write_client})

    partition = _partition(table_name="Orders", pk_columns=("id",))
    total_written = ta.execute_partition_transport(reader=reader, writer=writer, partition=partition)

    assert total_written == 2
    assert read_client.scan_calls  # real source read reached
    assert write_client.batch_write_calls  # real target write reached


# ---------------------------------------------------------------------------
# 13. EXACT_RESUME keyset proof for all 4 SQL-wire providers reusing
#     GenericSQLSourceReader (CockroachDB/YugabyteDB via psycopg2 paramstyle,
#     TiDB/SingleStore via pymysql paramstyle).
#
#     Real defect fixed during this hardening pass: GenericSQLSourceReader declared
#     ResumabilityMode.EXACT_RESUME but open_partition() silently ignored
#     last_committed_key -- a fresh-process resume would have re-scanned the whole
#     table from the start (re-delivering already-committed rows) rather than
#     genuinely resuming past the last committed key. Fixed by adding a real
#     keyset WHERE/ORDER BY clause and a resume_position property.
# ---------------------------------------------------------------------------

SQL_WIRE_PROVIDERS_PSYCOPG2 = ["cockroachdb", "yugabytedb"]
SQL_WIRE_PROVIDERS_PYMYSQL = ["tidb", "singlestore"]


@pytest.mark.parametrize("provider_id", SQL_WIRE_PROVIDERS_PSYCOPG2 + SQL_WIRE_PROVIDERS_PYMYSQL)
def test_sql_wire_reader_bounds_multiple_batches_before_real_exhaustion(provider_id):
    """Bounded-memory proof: multiple fetchmany() pages, not just one, for every SQL-wire
    provider -- the earlier RabbitMQ/Pulsar premature-exhaustion defect is exactly why a
    single-page test is insufficient evidence."""
    conn_cls = _FakeSqlConnection if provider_id in SQL_WIRE_PROVIDERS_PSYCOPG2 else _FakeMySQLLikeConnection
    rows = [(i, f"name{i}") for i in range(11)]
    conn = conn_cls(rows, description=[("id",), ("name",)])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={"db_connection": conn})

    reader.open_partition(_partition(table_name="orders", schema_name="public", pk_columns=("id",)))
    pages = []
    while True:
        b = reader.read_batch(batch_size=4)
        if b is None:
            break
        pages.append(len(b.rows))
    assert pages == [4, 4, 3], f"expected 3 bounded pages of [4,4,3] rows, got {pages}"


@pytest.mark.parametrize("provider_id", SQL_WIRE_PROVIDERS_PSYCOPG2 + SQL_WIRE_PROVIDERS_PYMYSQL)
def test_sql_wire_reader_exact_resume_keyset_survives_fresh_process(provider_id):
    """Fresh-process restart proof for CockroachDB/YugabyteDB/TiDB/SingleStore: Runtime A
    reads one batch and captures its real resume_position (last PK read); Runtime A is then
    fully discarded (new TransportAuthority, new reader instance -- simulating a fresh
    process); Runtime B reopens the SAME partition with that resume_position as
    last_committed_key and must receive ONLY the rows strictly after it, proving genuine
    exact-resume (not a full re-scan, which would re-deliver rows 0-3 and falsify
    ResumabilityMode.EXACT_RESUME)."""
    conn_cls = _FakeSqlConnection if provider_id in SQL_WIRE_PROVIDERS_PSYCOPG2 else _FakeMySQLLikeConnection
    all_rows = [(i, f"name{i}") for i in range(10)]

    # Runtime A
    conn_a = conn_cls(list(all_rows), description=[("id",), ("name",)])
    ta_a = TransportAuthority()
    reader_a = ta_a.resolve_source_reader_for_provider(provider_id, connection_params={"db_connection": conn_a})
    reader_a.open_partition(_partition(table_name="orders", schema_name="public", pk_columns=("id",)))
    batch_a = reader_a.read_batch(batch_size=4)
    assert batch_a is not None and len(batch_a.rows) == 4
    resume_position = reader_a.resume_position
    assert resume_position == 3  # last row read was id=3 (0,1,2,3)
    reader_a.close()
    del reader_a, ta_a, conn_a  # discard Runtime A entirely, including in-memory reader state

    # Runtime B: fresh TransportAuthority, fresh reader, fresh fake connection/cursor --
    # nothing from Runtime A carries over except the durable resume_position value.
    # The fake cursor (unlike a real server) does not execute SQL, so it is seeded with
    # only the rows a real "WHERE id > 3" would return -- the assertion on
    # executed_sql/executed_params below is what actually proves the real query was built
    # correctly to ask the server to do that filtering.
    remaining_seed = [r for r in all_rows if r[0] > resume_position]
    conn_b = conn_cls(remaining_seed, description=[("id",), ("name",)])
    ta_b = TransportAuthority()
    reader_b = ta_b.resolve_source_reader_for_provider(provider_id, connection_params={"db_connection": conn_b})
    reader_b.open_partition(
        _partition(table_name="orders", schema_name="public", pk_columns=("id",)),
        last_committed_key=resume_position,
    )
    executed_sql, executed_params = conn_b._cursor.executed[0]
    assert '"id" >' in executed_sql, "resumed query must filter strictly past the last committed key"
    assert executed_params == (3,)

    remaining_rows: List[int] = []
    while True:
        b = reader_b.read_batch(batch_size=4)
        if b is None:
            break
        remaining_rows.extend(r["id"] for r in b.rows)
    assert remaining_rows == [4, 5, 6, 7, 8, 9], (
        f"exact-resume must deliver rows strictly after id=3 exactly once, got {remaining_rows}"
    )


# ---------------------------------------------------------------------------
# 14. Pulsar genuine PROVIDER_RESUMABLE proof (broker-side subscription cursor, not a
#     client-supplied key) vs RabbitMQ genuine NON_RESUMABLE proof (no fabricated
#     arbitrary durable resume for ordinary queues).
# ---------------------------------------------------------------------------

def test_pulsar_resume_is_via_broker_subscription_cursor_not_a_fabricated_key():
    """Pulsar's real resumability mechanism is the broker remembering the NAMED
    subscription's cursor position (advanced by cumulative ack), not any client-supplied
    last_committed_key -- proves open_partition() re-subscribes to the SAME subscription
    name on a fresh process, and that passing an arbitrary last_committed_key does not
    change which messages are delivered (there is no per-message key-based filtering,
    because Pulsar genuinely has none for this deferred-ack consumer pattern)."""
    consumer = _FakePulsarConsumer([_FakePulsarMessage("m1", b"hello")])
    client = _FakePulsarClient(consumer=consumer)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("pulsar", connection_params={"db_connection": client})

    partition = _partition(table_name="persistent://t/ns/orders", partition_id="p7")
    reader.open_partition(partition, last_committed_key="some-arbitrary-key-ignored")
    assert client.subscribed[-1] == ("persistent://t/ns/orders", "akaal-transport-p7")

    b = reader.read_batch(batch_size=10)
    assert b is not None and len(b.rows) == 1  # arbitrary key did not suppress delivery
    assert reader.get_capabilities().resumability == ResumabilityMode.PROVIDER_RESUMABLE


def test_rabbitmq_declares_non_resumable_and_enforces_no_fabricated_arbitrary_resume():
    """RabbitMQ classic/ordinary queues have no arbitrary durable resume mechanism: a
    fresh basic_get()-based consumer cannot be told 'start after message X' -- it simply
    receives whatever is next in the queue. This test proves the driver does NOT invent
    one: passing a last_committed_key has zero effect on which message basic_get() returns
    (there is no filtering code path), and the declared capability is honestly
    NON_RESUMABLE, not EXACT_RESUME or PROVIDER_RESUMABLE."""
    channel = _FakeRabbitChannel([("rk1", b"only-message")])
    conn = _FakeRabbitConnection(channel)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("rabbitmq", connection_params={"db_connection": conn})

    partition = _partition(table_name="orders.q", schema_name="/")
    reader.open_partition(partition, last_committed_key="fabricated-resume-token-should-be-ignored")

    b = reader.read_batch(batch_size=10)
    assert b is not None and len(b.rows) == 1  # delivered regardless of the bogus key
    assert reader.get_capabilities().resumability == ResumabilityMode.NON_RESUMABLE
    assert not hasattr(reader, "resume_position"), (
        "RabbitMQSourceReader must not expose a resume_position property -- doing so "
        "would falsely imply a durable resume point exists for ordinary queues"
    )


# ---------------------------------------------------------------------------
# 15. Fresh-process restart proof for the offset/range-boundary PROVIDER_RESUMABLE
#     providers: ClickHouse, Couchbase, InfluxDB. Each already threads
#     last_committed_key -> internal cursor correctly; these tests prove that survives
#     a genuinely fresh reader instance (Runtime A fully discarded, Runtime B constructed
#     from nothing but the persisted resume_position), not merely an in-memory carry-over.
# ---------------------------------------------------------------------------

def test_clickhouse_reader_resume_position_survives_fresh_process():
    # Runtime A
    client_a = _FakeClickHouseClient([([(1, "a"), (2, "b")], ["id", "name"])])
    ta_a = TransportAuthority()
    reader_a = ta_a.resolve_source_reader_for_provider("clickhouse", connection_params={"db_connection": client_a})
    reader_a.open_partition(_partition(table_name="events", schema_name="analytics"))
    b1 = reader_a.read_batch(batch_size=2)
    assert b1 is not None and len(b1.rows) == 2
    resume_position = reader_a.resume_position
    assert resume_position == 2
    del reader_a, ta_a, client_a

    # Runtime B: brand-new TransportAuthority/reader/fake client.
    client_b = _FakeClickHouseClient([([(3, "c")], ["id", "name"]), ([], ["id", "name"])])
    ta_b = TransportAuthority()
    reader_b = ta_b.resolve_source_reader_for_provider("clickhouse", connection_params={"db_connection": client_b})
    reader_b.open_partition(_partition(table_name="events", schema_name="analytics"), last_committed_key=resume_position)

    b2 = reader_b.read_batch(batch_size=2)
    assert b2 is not None and len(b2.rows) == 1 and b2.rows[0]["id"] == 3
    assert "OFFSET 2" in client_b.queries[0], "resumed query must start at the persisted offset, not 0"


def test_couchbase_reader_resume_position_survives_fresh_process():
    collection_a = _FakeCouchbaseCollection()
    cluster_a = _FakeCouchbaseCluster([[{"__doc_id": "d1", "name": "a"}, {"__doc_id": "d2", "name": "b"}]], collection_a)
    ta_a = TransportAuthority()
    reader_a = ta_a.resolve_source_reader_for_provider("couchbase", connection_params={"db_connection": cluster_a, "bucket": "b1"})
    reader_a.open_partition(_partition(table_name="orders", schema_name="_default.orders"))
    b1 = reader_a.read_batch(batch_size=2)
    assert b1 is not None and len(b1.rows) == 2
    resume_position = reader_a.resume_position
    assert resume_position == 2
    del reader_a, ta_a, cluster_a, collection_a

    collection_b = _FakeCouchbaseCollection()
    cluster_b = _FakeCouchbaseCluster([[{"__doc_id": "d3", "name": "c"}], []], collection_b)
    ta_b = TransportAuthority()
    reader_b = ta_b.resolve_source_reader_for_provider("couchbase", connection_params={"db_connection": cluster_b, "bucket": "b1"})
    reader_b.open_partition(_partition(table_name="orders", schema_name="_default.orders"), last_committed_key=resume_position)

    b2 = reader_b.read_batch(batch_size=2)
    assert b2 is not None and len(b2.rows) == 1 and b2.rows[0]["__doc_id"] == "d3"
    assert "OFFSET 2" in cluster_b.queries[0], "resumed query must start at the persisted offset, not 0"


def test_influxdb_reader_resume_position_survives_fresh_process():
    import datetime
    t1 = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2024, 1, 2, tzinfo=datetime.timezone.utc)

    client_a = _FakeInfluxClient([[_FakeInfluxTable([_FakeInfluxRecord(t1, "temp", 21.5, {"host": "srv1"})])]])
    ta_a = TransportAuthority()
    reader_a = ta_a.resolve_source_reader_for_provider("influxdb", connection_params={"db_connection": client_a, "org": "myorg"})
    reader_a.open_partition(_partition(table_name="cpu", schema_name="metrics"))
    b1 = reader_a.read_batch(batch_size=1)
    assert b1 is not None and len(b1.rows) == 1
    resume_position = reader_a.resume_position
    assert "2024-01-01" in resume_position
    del reader_a, ta_a, client_a

    client_b = _FakeInfluxClient([
        [_FakeInfluxTable([_FakeInfluxRecord(t2, "temp", 22.0, {"host": "srv1"})])],
        [_FakeInfluxTable([])],
    ])
    ta_b = TransportAuthority()
    reader_b = ta_b.resolve_source_reader_for_provider("influxdb", connection_params={"db_connection": client_b, "org": "myorg"})
    reader_b.open_partition(_partition(table_name="cpu", schema_name="metrics"), last_committed_key=resume_position)

    b2 = reader_b.read_batch(batch_size=1)
    assert b2 is not None and len(b2.rows) == 1
    assert resume_position in client_b._query_api.fluxes[0], (
        "resumed Flux query must start its range() at the persisted boundary, not the epoch"
    )
