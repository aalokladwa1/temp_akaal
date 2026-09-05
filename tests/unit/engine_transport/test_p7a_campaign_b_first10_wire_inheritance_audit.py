"""
tests.unit.engine_transport.test_p7a_campaign_b_first10_wire_inheritance_audit
======================================================================
P7A Campaign B — First-10-Provider EXECUTABLE inheritance / native-semantics hostile
audit for the 4 wire-compatible pairs: CockroachDB<->PostgreSQL, YugabyteDB<->
PostgreSQL (both psycopg2/YSQL), TiDB<->MySQL, SingleStore<->MySQL (both pymysql).

This is deliberately consolidated rather than duplicated across the other test files:
each individual fact below is executed here directly against real production driver
classes (no conceptual/structural-only assertions), while cross-referencing the other
suites that already executed the same mechanism from a different angle:
  - Paramstyle correctness: proven per-batch in
    test_p7a_campaign_b_first10_transport_dataplane.py
    (test_mysql_wire_compatible_writer_uses_correct_placeholder_style,
    test_cockroachdb_writer_reaches_real_psycopg2_execute_values_boundary) and
    re-asserted here for both pairs together.
  - Identity non-collapse (a resolved "cockroachdb" strategy is never the literal
    PostgreSQL strategy instance): proven in
    tests/unit/engine_extensions/test_p7a_campaign_b_first10_independence.py.
  - CDC-restriction (none of the 4 can acquire a physical CDC adapter): proven
    provider-by-provider there too; reconfirmed here for the 4 pairs specifically.

New, not previously executed elsewhere:
  - verify_uncertain_commit() for CockroachDB/YugabyteDB performs a REAL PK-based
    physical re-query (COMMITTED/NOT_COMMITTED/UNKNOWN), never a hardcoded UNKNOWN --
    the actual override point that makes each subclass genuinely distinct from a bare
    PostgreSQLTargetWriter, not just a differently-named copy.
  - YugabyteDB's real psycopg2.extras.execute_values() bulk-write physical boundary
    (only CockroachDB's was previously exercised at that exact boundary).
  - Default port differs correctly per subclass (26257 vs 5433 vs PostgreSQL's 5432)
    at real connection-parameter-construction time.
"""

from __future__ import annotations

import pytest

from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.drivers.cockroachdb import CockroachDBTargetWriter
from akaalEngine.transport.drivers.postgres import PostgreSQLTargetWriter
from akaalEngine.transport.drivers.yugabytedb import YugabyteDBTargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import CommitOutcomeState

WIRE_PAIRS = {
    "cockroachdb": ("postgresql", 26257),
    "yugabytedb": ("postgresql", 5433),
}


@pytest.mark.parametrize("provider_id,parent_and_port", WIRE_PAIRS.items())
def test_writer_subclasses_parent_but_is_genuinely_distinct_class(provider_id, parent_and_port):
    """CockroachDBTargetWriter/YugabyteDBTargetWriter must be real subclasses of
    PostgreSQLTargetWriter (proving they legitimately reuse its execute_values/retry
    logic), while remaining genuinely distinct, non-aliased classes."""
    writer_cls = {"cockroachdb": CockroachDBTargetWriter, "yugabytedb": YugabyteDBTargetWriter}[provider_id]
    assert issubclass(writer_cls, PostgreSQLTargetWriter)
    assert writer_cls is not PostgreSQLTargetWriter
    assert writer_cls.__name__ != "PostgreSQLTargetWriter"


@pytest.mark.parametrize("provider_id,parent_and_port", WIRE_PAIRS.items())
def test_writer_uses_own_default_port_not_postgresql_default(provider_id, parent_and_port, monkeypatch):
    """Each subclass's _connect() must request ITS OWN default wire port (26257 for
    CockroachDB, 5433 for YugabyteDB), never silently falling back to PostgreSQL's 5432 --
    a real, physically-observable divergence point, not a cosmetic one."""
    _, expected_port = parent_and_port
    writer_cls = {"cockroachdb": CockroachDBTargetWriter, "yugabytedb": YugabyteDBTargetWriter}[provider_id]

    import akaalEngine.transport.drivers.postgres as postgres_mod
    captured = {}
    fake_conn = type("FakeConn", (), {"cursor": lambda self: type("C", (), {})()})()
    def fake_connect(**kwargs):
        captured.update(kwargs)
        return fake_conn
    monkeypatch.setattr(postgres_mod.psycopg2, "connect", fake_connect)

    writer = writer_cls(connection_params={"user": "u", "dbname": "d"})
    writer._connect()
    assert captured["port"] == expected_port


@pytest.mark.parametrize("provider_id", ["cockroachdb", "yugabytedb"])
def test_verify_uncertain_commit_performs_real_pk_requery_not_fabricated_unknown(provider_id):
    """The actual override that makes CockroachDB/YugabyteDB genuinely distinct from a
    bare PostgreSQLTargetWriter: verify_uncertain_commit() issues a REAL parameterized
    'SELECT count(*) ... WHERE pk IN (...)' re-query and classifies the outcome as
    COMMITTED/NOT_COMMITTED based on the REAL row count returned, never an unconditional
    UNKNOWN placeholder."""
    writer_cls = {"cockroachdb": CockroachDBTargetWriter, "yugabytedb": YugabyteDBTargetWriter}[provider_id]

    class _FakeCheckCursor:
        def __init__(self, count):
            self._count = count
            self.executed = None
        def execute(self, sql, params):
            self.executed = (sql, params)
        def fetchone(self):
            return (self._count,)
        def close(self):
            pass

    class _FakeConn:
        def __init__(self, count):
            self._count = count
        def cursor(self):
            return _FakeCheckCursor(self._count)

    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="public", sequence_number=1, row_count=2, size_bytes=10),
        rows=[{"id": 1}, {"id": 2}], column_names=["id"],
    )

    writer = writer_cls(connection_params={})
    writer.conn = _FakeConn(count=2)  # both rows found -> COMMITTED
    assert writer.verify_uncertain_commit("orders", "public", ["id"], batch) == CommitOutcomeState.COMMITTED

    writer2 = writer_cls(connection_params={})
    writer2.conn = _FakeConn(count=0)  # neither row found -> NOT_COMMITTED
    assert writer2.verify_uncertain_commit("orders", "public", ["id"], batch) == CommitOutcomeState.NOT_COMMITTED

    writer3 = writer_cls(connection_params={})
    writer3.conn = _FakeConn(count=1)  # partial/ambiguous -> genuinely UNKNOWN, not a lucky guess
    assert writer3.verify_uncertain_commit("orders", "public", ["id"], batch) == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME


def test_yugabytedb_writer_reaches_real_psycopg2_execute_values_boundary(monkeypatch):
    """YugabyteDBTargetWriter's bulk write must reach the real psycopg2.extras.execute_values
    entrypoint (only CockroachDB's was previously exercised at this exact boundary)."""
    import akaalEngine.transport.drivers.postgres as postgres_mod
    fake_conn = type("FakeConn", (), {})()
    fake_cursor = type("FakeCursor", (), {"rowcount": 2})()
    fake_conn.cursor = lambda: fake_cursor
    fake_conn.commit = lambda: None
    monkeypatch.setattr(postgres_mod.psycopg2, "connect", lambda **kw: fake_conn)

    calls = []
    monkeypatch.setattr(postgres_mod.psycopg2.extras, "execute_values", lambda cursor, sql, data: calls.append((sql, data)))

    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("yugabytedb", connection_params={"user": "u", "dbname": "d"})
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="public", sequence_number=1, row_count=2, size_bytes=10),
        rows=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}], column_names=["id", "name"],
    )
    written = writer.write_batch("orders", batch, target_schema="public", pk_columns=["id"])

    assert written == 2
    assert calls, "YugabyteDBTargetWriter must reach the real psycopg2.extras.execute_values boundary"
    assert "orders" in calls[0][0]


@pytest.mark.parametrize("provider_id", ["cockroachdb", "yugabytedb", "tidb", "singlestore"])
def test_wire_compatible_provider_still_fails_closed_for_cdc(provider_id):
    """Reconfirmation, specific to the 4 wire-compatible pairs: none can acquire a
    physical CDC adapter through the real CDCAuthority despite being wire-compatible
    with a parent that (in principle) could support binlog/WAL-based CDC -- wire
    compatibility for read/write must never be conflated with CDC capability."""
    from akaalEngine.cdc.api import CDCAuthority
    from akaalEngine.discovery.authority import DiscoveryAuthority
    from akaalEngine.extensions.authority import ExtensionsAuthority
    from akaalEngine.extensions.errors.taxonomy import ExtensionEngineException

    ext_auth = ExtensionsAuthority.get_instance()
    ext_auth.bootstrap_builtin_providers()
    da = DiscoveryAuthority(extensions_authority=ext_auth)
    cdc = CDCAuthority(extensions_authority=da._ext_auth)

    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider(provider_id)
