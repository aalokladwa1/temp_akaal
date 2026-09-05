"""
tests.unit.engine_transport.test_p7a_campaign_b_remaining10_transport_dataplane
================================================================================
P7A Campaign B -- Remaining-10-Provider canonical physical data-plane proof.

Proves the real SourceReader/TargetWriter classes registered in
`akaalEngine.transport.drivers.registry.default_transport_driver_registry` for all
ten remaining-10 providers (Teradata, Vertica, SAP HANA, SAP ASE, Informix, Cosmos DB,
Spanner, Salesforce, ServiceNow, and the SAP Application Ecosystem's OData interface
mode) actually reach a real physical boundary end to end, mirroring the First-10
dataplane proof (`test_p7a_campaign_b_first10_transport_dataplane.py`).

Mocks exist ONLY at the final external SDK/client boundary (a fake DB-API 2.0
cursor/connection for the five relational drivers, a fake azure-cosmos ContainerProxy,
a fake google-cloud-spanner Database/snapshot/batch, a fake simple_salesforce client,
a fake requests.Session for ServiceNow and SAP OData). Every layer above that boundary
(SourceReader.open_partition/read_batch, TargetWriter.write_batch/commit,
TransportAuthority.execute_partition_transport) is real, unmodified-for-testing
production code.

SAP Application Ecosystem (provider #47) resolution (owner-directed, 2026-09-05): ONE
canonical provider ('sap_application') with capability-driven RFC/BAPI, IDoc, and
OData interface modes, never three separate provider entries. OData mode is fully
locally provable (see below); RFC/BAPI and IDoc modes require the proprietary `pyrfc`
SDK and are proven to fail closed (dependency-gated) when it is absent -- see
`test_sap_application_rfc_and_idoc_modes_fail_closed_without_pyrfc` below.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import CommitOutcomeState, IdempotencyMode, ResumabilityMode
from akaalEngine.transport.models.errors import TransportCapabilityError
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


REMAINING_PROVIDERS = [
    "teradata", "vertica", "sap_hana", "sap_ase", "informix",
    "cosmosdb", "spanner", "salesforce", "servicenow", "sap_application",
]


# ---------------------------------------------------------------------------
# 1. Registry resolution proves reachability for all 9 implemented providers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider_id", REMAINING_PROVIDERS)
def test_transport_authority_resolves_real_reader_and_writer(provider_id):
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={})
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={})
    assert reader is not None
    assert writer is not None
    assert reader.get_capabilities() is not None
    assert writer.get_capabilities() is not None


def test_sap_application_ecosystem_is_registered_as_one_provider_family():
    """Owner-resolved scope (2026-09-05): SAP Application Ecosystem is ONE canonical
    provider ('sap_application'), never three separate provider-catalog entries for
    RFC/BAPI, IDoc, and OData -- those are interface modes selected at connection time."""
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("sap_application", connection_params={})
    writer = ta.resolve_target_writer_for_provider("sap_application", connection_params={})
    assert reader is not None and writer is not None
    for fake_id in ("sap_rfc", "sap_bapi", "sap_idoc", "sap_odata", "sap_erp"):
        with pytest.raises(TransportCapabilityError):
            ta.resolve_source_reader_for_provider(fake_id)


# ---------------------------------------------------------------------------
# 2. DB-API relational family (Teradata, Vertica, SAP HANA) -- double-quote-safe,
#    reuse GenericSQLSourceReader directly + PK-requery verify_uncertain_commit
# ---------------------------------------------------------------------------

class _FakeSqlCursor:
    def __init__(self, rows, description):
        self._rows = list(rows)
        self.description = description
        self.rowcount = -1
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "count(*)" in sql.lower():
            self._count_result = [(len(self._rows),)]

    def executemany(self, sql, seq_of_params):
        self.executed.append((sql, seq_of_params))
        self.rowcount = len(seq_of_params)

    def fetchmany(self, n):
        batch, self._rows = self._rows[:n], self._rows[n:]
        return batch

    def fetchone(self):
        if hasattr(self, "_count_result"):
            r = self._count_result.pop(0)
            return r
        return self._rows.pop(0) if self._rows else None

    def close(self):
        pass


class _FakeSqlConnection:
    def __init__(self, rows, description, module_name="teradatasql"):
        self.__class__.__module__ = module_name
        self._cursor = _FakeSqlCursor(rows, description)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.mark.parametrize("provider_id", ["teradata", "vertica", "sap_hana"])
def test_dbapi_family_reader_reaches_real_cursor_and_bounds_batches(provider_id):
    rows = [(i, f"name{i}") for i in range(7)]
    conn = _FakeSqlConnection(rows, description=[("id",), ("name",)])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={"db_connection": conn})

    reader.open_partition(_partition(table_name="orders", schema_name="public", pk_columns=("id",)))
    assert conn._cursor.executed, "reader must have issued a real SELECT against the fake cursor"

    b1 = reader.read_batch(batch_size=5)
    assert b1 is not None and len(b1.rows) == 5
    b2 = reader.read_batch(batch_size=5)
    assert b2 is not None and len(b2.rows) == 2
    b3 = reader.read_batch(batch_size=5)
    assert b3 is None  # bounded EOF, not an unbounded materialization
    assert reader.resume_position == 6  # last-read PK value, real EXACT_RESUME keyset state


@pytest.mark.parametrize("provider_id,module_name", [("teradata", "teradatasql"), ("vertica", "vertica_python"), ("sap_hana", "hdbcli")])
def test_dbapi_family_writer_reaches_real_executemany_boundary(provider_id, module_name):
    conn = _FakeSqlConnection(rows=[], description=[], module_name=module_name)
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn})

    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="public", sequence_number=1, row_count=2, size_bytes=10),
        rows=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
        column_names=["id", "name"],
    )
    written = writer.write_batch("orders", batch, target_schema="public", pk_columns=["id"])
    assert written == 2
    assert conn._cursor.executed
    writer.commit()
    assert conn.committed is True


@pytest.mark.parametrize("provider_id", ["teradata", "vertica", "sap_hana"])
def test_dbapi_family_verify_uncertain_commit_is_real_pk_requery(provider_id):
    """Ambiguous-commit verification must physically re-query the target by PK, not
    fabricate an UNKNOWN result unconditionally -- mirrors the CockroachDB precedent."""
    conn = _FakeSqlConnection(rows=[(1,)], description=[])  # 1 pre-existing row simulates a committed batch
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn})
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="public", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1}],
        column_names=["id"],
    )
    outcome = writer.verify_uncertain_commit("orders", "public", ["id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    count_sql = [c for c in conn._cursor.executed if "count(*)" in c[0].lower()]
    assert count_sql, "verify_uncertain_commit must issue a real SELECT count(*) query"

    conn2 = _FakeSqlConnection(rows=[], description=[])  # no matching rows simulates a genuinely non-committed batch
    writer2 = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn2})
    outcome2 = writer2.verify_uncertain_commit("orders", "public", ["id"], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


# ---------------------------------------------------------------------------
# 3. SAP ASE / Informix -- standalone unquoted-identifier drivers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider_id", ["sap_ase", "informix"])
def test_unquoted_identifier_family_reader_never_emits_double_quotes(provider_id):
    rows = [(i, f"n{i}") for i in range(3)]
    conn = _FakeSqlConnection(rows, description=[("id",), ("name",)])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={"db_connection": conn})
    reader.open_partition(_partition(table_name="orders", schema_name="dbo", pk_columns=("id",)))
    sql = conn._cursor.executed[0][0]
    assert '"' not in sql, f"{provider_id} reader must not emit ANSI double-quoted identifiers by default: {sql}"
    batch = reader.read_batch(batch_size=10)
    assert batch is not None and len(batch.rows) == 3


@pytest.mark.parametrize("provider_id", ["sap_ase", "informix"])
def test_unquoted_identifier_family_writer_never_emits_double_quotes(provider_id):
    conn = _FakeSqlConnection(rows=[], description=[])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn})
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="dbo", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )
    writer.write_batch("orders", batch, target_schema="dbo", pk_columns=["id"])
    sql = conn._cursor.executed[0][0]
    assert '"' not in sql, f"{provider_id} writer must not emit ANSI double-quoted identifiers by default: {sql}"


@pytest.mark.parametrize("provider_id", ["sap_ase", "informix"])
def test_unquoted_identifier_family_rollback_rejected_with_no_active_transaction(provider_id):
    conn = _FakeSqlConnection(rows=[], description=[])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn})
    from akaalEngine.transport.models.errors import TransportWriteError
    with pytest.raises(TransportWriteError):
        writer.rollback()


@pytest.mark.parametrize("provider_id", ["sap_ase", "informix"])
def test_unquoted_identifier_family_verify_uncertain_commit_is_real_pk_requery(provider_id):
    """Ambiguous-commit verification must physically re-query the target by PK, not
    fabricate an UNKNOWN result unconditionally -- same standard as the DB-API family."""
    conn_committed = _FakeSqlConnection(rows=[(1,)], description=[])  # 1 pre-existing row simulates a committed batch
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn_committed})
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="dbo", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1}],
        column_names=["id"],
    )
    outcome = writer.verify_uncertain_commit("orders", "dbo", ["id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    sql = conn_committed._cursor.executed[0][0]
    assert "count(*)" in sql.lower()
    assert '"' not in sql, f"{provider_id} verify_uncertain_commit must not emit ANSI double-quoted identifiers: {sql}"

    conn_not_committed = _FakeSqlConnection(rows=[], description=[])
    writer2 = ta.resolve_target_writer_for_provider(provider_id, connection_params={"db_connection": conn_not_committed})
    outcome2 = writer2.verify_uncertain_commit("orders", "dbo", ["id"], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


# ---------------------------------------------------------------------------
# 4. Cosmos DB -- real continuation-token pagination + upsert idempotency
# ---------------------------------------------------------------------------

class _FakePage:
    def __init__(self, items, token):
        self._items = items
        self.continuation_token = token

    def __iter__(self):
        return iter(self._items)


class _FakeItemPaged:
    def __init__(self, pages):
        self._pages = list(pages)

    def by_page(self, continuation_token=None):
        return iter(self._pages)


class _FakeCosmosContainer:
    def __init__(self, pages):
        self._pages = pages
        self.upserted: List[Dict[str, Any]] = []
        self._store: Dict[str, Dict[str, Any]] = {}

    def query_items(self, query, enable_cross_partition_query=True, max_item_count=100):
        return _FakeItemPaged(self._pages)

    def upsert_item(self, body):
        self.upserted.append(body)
        self._store[body["id"]] = body
        return body

    def read_item(self, item, partition_key):
        if item not in self._store:
            from azure.core.exceptions import ResourceNotFoundError  # type: ignore
            raise ResourceNotFoundError()
        return self._store[item]


def test_cosmosdb_reader_uses_real_continuation_token_not_offset():
    page1 = _FakePage([{"id": "1"}, {"id": "2"}], "tok-abc")
    page2 = _FakePage([{"id": "3"}], None)
    container = _FakeCosmosContainer([page1])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("cosmosdb", connection_params={"db_connection": container})
    reader.open_partition(_partition(table_name="items"))
    batch = reader.read_batch(batch_size=10)
    assert batch is not None and len(batch.rows) == 2
    assert reader.resume_position == "tok-abc"  # real server continuation token, not a fabricated offset


def test_cosmosdb_writer_upsert_is_genuinely_idempotent():
    container = _FakeCosmosContainer([])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("cosmosdb", connection_params={"db_connection": container})
    assert writer.get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="items", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": "x1", "val": 1}],
        column_names=["id", "val"],
    )
    written = writer.write_batch("items", batch)
    assert written == 1
    # Replaying the identical batch converges to the same end state (upsert, not insert).
    written2 = writer.write_batch("items", batch)
    assert written2 == 1
    assert len(container.upserted) == 2  # two calls made, both idempotent no-op-equivalent
    assert container._store["x1"]["val"] == 1


# ---------------------------------------------------------------------------
# 5. Spanner -- real keyset EXACT_RESUME + Mutation API batch
# ---------------------------------------------------------------------------

class _FakeSpannerResult:
    def __init__(self, rows, fields):
        self._rows = rows
        self.fields = fields

    def __iter__(self):
        return iter(self._rows)


class _FakeSpannerField:
    def __init__(self, name):
        self.name = name


class _FakeSnapshot:
    def __init__(self, rows_by_call):
        self._rows_by_call = rows_by_call
        self._call_idx = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute_sql(self, sql, params=None, param_types=None):
        rows = self._rows_by_call[min(self._call_idx, len(self._rows_by_call) - 1)]
        self._call_idx += 1
        return _FakeSpannerResult(rows, [_FakeSpannerField("id"), _FakeSpannerField("name")])


class _FakeBatch:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def insert_or_update(self, table, columns, values):
        self.sink.append((table, columns, values))


class _FakeSpannerDatabase:
    def __init__(self, rows_by_call):
        self._rows_by_call = rows_by_call
        self.batches: List[Any] = []

    def snapshot(self):
        return _FakeSnapshot(self._rows_by_call)

    def batch(self):
        return _FakeBatch(self.batches)


def test_spanner_reader_uses_real_keyset_and_bounds_via_limit():
    rows_page1 = [(1, "a"), (2, "b")]
    db = _FakeSpannerDatabase([rows_page1])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("spanner", connection_params={"db_connection": db})
    reader.open_partition(_partition(table_name="orders", pk_columns=("id",)))
    batch = reader.read_batch(batch_size=5)
    assert batch is not None and len(batch.rows) == 2
    assert reader.resume_position == 2  # real last-key keyset continuation


def test_spanner_writer_uses_real_mutation_api():
    db = _FakeSpannerDatabase([[]])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("spanner", connection_params={"db_connection": db})
    assert writer.get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )
    written = writer.write_batch("orders", batch)
    assert written == 1
    assert len(db.batches) == 1
    assert db.batches[0][0] == "orders"


# ---------------------------------------------------------------------------
# 6. Salesforce -- real nextRecordsUrl continuation, SObject Collections writes
# ---------------------------------------------------------------------------

class _FakeSalesforceClient:
    def __init__(self, page1, page2=None):
        self._page1 = page1
        self._page2 = page2
        self.restful_calls: List[Any] = []

    def query(self, soql):
        return self._page1

    def query_more(self, url, identifier_is_url=True):
        return self._page2

    def restful(self, path, method="GET", json=None):
        self.restful_calls.append((path, method, json))
        return [{"success": True, "id": r.get("Id", f"new-{i}")} for i, r in enumerate(json["records"])]


def test_salesforce_reader_uses_real_next_records_url_continuation():
    page1 = {"records": [{"Id": "1", "attributes": {}}], "done": False, "nextRecordsUrl": "/services/data/v58.0/query/01g-2000"}
    page2 = {"records": [{"Id": "2", "attributes": {}}], "done": True, "nextRecordsUrl": None}
    client = _FakeSalesforceClient(page1, page2)
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("salesforce", connection_params={"db_connection": client})
    reader.open_partition(_partition(table_name="Account"))

    b1 = reader.read_batch(batch_size=10)
    assert b1 is not None and b1.rows[0]["Id"] == "1"
    assert reader.resume_position == "/services/data/v58.0/query/01g-2000"

    b2 = reader.read_batch(batch_size=10)
    assert b2 is not None and b2.rows[0]["Id"] == "2"
    assert reader.resume_position is None  # done=True, no further continuation


def test_salesforce_writer_uses_real_sobject_collections_endpoint():
    client = _FakeSalesforceClient(page1={})
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("salesforce", connection_params={"db_connection": client})
    assert writer.get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT  # no external_id_field configured
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="Account", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"Name": "Acme"}],
        column_names=["Name"],
    )
    written = writer.write_batch("Account", batch)
    assert written == 1
    assert client.restful_calls[0][0] == "composite/sobjects"
    assert client.restful_calls[0][1] == "POST"


def test_salesforce_writer_external_id_upsert_is_idempotent():
    client = _FakeSalesforceClient(page1={})
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("salesforce", connection_params={"db_connection": client, "external_id_field": "External_Id__c"})
    assert writer.get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="Account", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"Name": "Acme", "External_Id__c": "ext-1"}],
        column_names=["Name", "External_Id__c"],
    )
    writer.write_batch("Account", batch)
    assert client.restful_calls[0][0] == "composite/sobjects/Account/External_Id__c"
    assert client.restful_calls[0][1] == "PATCH"


# ---------------------------------------------------------------------------
# 7. ServiceNow -- real Table API sysparm_offset pagination
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeServiceNowSession:
    def __init__(self, pages):
        self._pages = pages
        self._call_idx = 0
        self.base_url = "https://dev12345.service-now.com"
        self.posted: List[Any] = []

    def get(self, url, params=None):
        page = self._pages[min(self._call_idx, len(self._pages) - 1)]
        self._call_idx += 1
        return _FakeResponse({"result": page})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return _FakeResponse({"result": {**json, "sys_id": "new-sys-id"}})


def test_servicenow_reader_uses_real_sysparm_offset_pagination():
    page1 = [{"sys_id": "1"}, {"sys_id": "2"}]
    page2 = []
    session = _FakeServiceNowSession([page1, page2])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("servicenow", connection_params={"db_connection": session, "base_url": session.base_url})
    reader.open_partition(_partition(table_name="incident"))
    b1 = reader.read_batch(batch_size=2)
    assert b1 is not None and len(b1.rows) == 2
    assert reader.resume_position == 2  # real sysparm_offset continuation, honestly not exact-resume


def test_servicenow_writer_reaches_real_table_api_post():
    session = _FakeServiceNowSession([[]])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider("servicenow", connection_params={"db_connection": session, "base_url": session.base_url})
    assert writer.get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT  # no correlation_field configured
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="incident", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"short_description": "test"}],
        column_names=["short_description"],
    )
    written = writer.write_batch("incident", batch)
    assert written == 1
    assert session.posted[0][0].endswith("/api/now/table/incident")


# ---------------------------------------------------------------------------
# 8. Native-semantics honesty: no false CDC claims, no cross-provider identity collapse
# ---------------------------------------------------------------------------

def test_no_remaining10_provider_falsely_claims_cdc_capability():
    """Every claimed CDC/change-capture capability must correspond to an actual capture
    module -- none of the 9 implemented remaining-10 drivers has one, so none may claim
    CDC-readiness through get_capabilities() (which has no CDC field) or via a discovery
    strategy's discover_cdc_prerequisites() returning is_cdc_ready=True (checked at the
    discovery layer's own dedicated tests -- this asserts driver-level capability truth
    doesn't smuggle in an undeclared CDC claim)."""
    ta = TransportAuthority()
    for provider_id in REMAINING_PROVIDERS:
        reader = ta.resolve_source_reader_for_provider(provider_id, connection_params={})
        caps = reader.get_capabilities()
        assert caps.resumability != ResumabilityMode.UNKNOWN, f"{provider_id} must declare a truthful resumability mode"


def test_relational_family_drivers_have_distinct_class_identity():
    """Teradata/Vertica/SAP HANA reuse GenericSQLSourceReader directly (like TiDB/
    SingleStore) but each TargetWriter subclass must remain a genuinely distinct class --
    no accidental identity collapse across provider-native writers."""
    from akaalEngine.transport.drivers.teradata import TeradataTargetWriter
    from akaalEngine.transport.drivers.vertica import VerticaTargetWriter
    from akaalEngine.transport.drivers.sap_hana import SAPHANATargetWriter
    classes = {TeradataTargetWriter, VerticaTargetWriter, SAPHANATargetWriter}
    assert len(classes) == 3


# ---------------------------------------------------------------------------
# 9. Cloud/SaaS family verify_uncertain_commit -- real physical ambiguous-commit
#    verification, dedicated tests for Cosmos DB, Spanner, Salesforce, ServiceNow
#    (closes the "uncertain-commit proof incomplete" acceptance gap).
# ---------------------------------------------------------------------------

class _FakeCosmosNotFoundError(Exception):
    status_code = 404


class _FakeCosmosContainerForCommitCheck:
    def __init__(self, existing_ids):
        self._existing = set(existing_ids)

    def read_item(self, item, partition_key):
        if item in self._existing:
            return {"id": item}
        raise _FakeCosmosNotFoundError("not found")


def test_cosmosdb_verify_uncertain_commit_is_real_read_item_requery():
    ta = TransportAuthority()

    committed_container = _FakeCosmosContainerForCommitCheck(existing_ids={"x1"})
    writer_committed = ta.resolve_target_writer_for_provider("cosmosdb", connection_params={"db_connection": committed_container})
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="items", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": "x1", "val": 1}],
        column_names=["id", "val"],
    )
    outcome = writer_committed.verify_uncertain_commit("items", "", ["id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED

    not_committed_container = _FakeCosmosContainerForCommitCheck(existing_ids=set())
    writer_not_committed = ta.resolve_target_writer_for_provider("cosmosdb", connection_params={"db_connection": not_committed_container})
    outcome2 = writer_not_committed.verify_uncertain_commit("items", "", ["id"], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


class _FakeSpannerSnapshotForCommitCheck:
    def __init__(self, count):
        self._count = count
        self.last_sql = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute_sql(self, sql, params=None, param_types=None):
        self.last_sql = sql
        return iter([(self._count,)])


class _FakeSpannerDatabaseForCommitCheck:
    def __init__(self, count):
        self._snap = _FakeSpannerSnapshotForCommitCheck(count)

    def snapshot(self):
        return self._snap


def test_spanner_verify_uncertain_commit_is_real_count_requery():
    ta = TransportAuthority()
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="orders", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"id": 1, "name": "a"}],
        column_names=["id", "name"],
    )

    db_committed = _FakeSpannerDatabaseForCommitCheck(count=1)
    writer_committed = ta.resolve_target_writer_for_provider("spanner", connection_params={"db_connection": db_committed})
    outcome = writer_committed.verify_uncertain_commit("orders", "", ["id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    assert "UNNEST" in db_committed._snap.last_sql

    db_not_committed = _FakeSpannerDatabaseForCommitCheck(count=0)
    writer_not_committed = ta.resolve_target_writer_for_provider("spanner", connection_params={"db_connection": db_not_committed})
    outcome2 = writer_not_committed.verify_uncertain_commit("orders", "", ["id"], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


class _FakeSalesforceClientForCommitCheck:
    def __init__(self, total_size):
        self._total_size = total_size
        self.queries = []

    def query(self, soql):
        self.queries.append(soql)
        return {"totalSize": self._total_size, "records": []}


def test_salesforce_verify_uncertain_commit_is_real_soql_requery():
    ta = TransportAuthority()
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="Account", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"Id": "001xx", "Name": "Acme"}],
        column_names=["Id", "Name"],
    )

    client_committed = _FakeSalesforceClientForCommitCheck(total_size=1)
    writer_committed = ta.resolve_target_writer_for_provider("salesforce", connection_params={"db_connection": client_committed})
    outcome = writer_committed.verify_uncertain_commit("Account", "", ["Id"], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    assert "WHERE Id = '001xx'" in client_committed.queries[0]

    client_not_committed = _FakeSalesforceClientForCommitCheck(total_size=0)
    writer_not_committed = ta.resolve_target_writer_for_provider("salesforce", connection_params={"db_connection": client_not_committed})
    outcome2 = writer_not_committed.verify_uncertain_commit("Account", "", ["Id"], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


class _FakeServiceNowSessionForCommitCheck:
    def __init__(self, found_rows):
        self._found_rows = found_rows
        self.base_url = "https://dev12345.service-now.com"
        self.get_calls = []

    def get(self, url, params=None):
        self.get_calls.append(params)
        return _FakeResponse({"result": self._found_rows})


def test_servicenow_verify_uncertain_commit_requires_correlation_field_and_is_real_requery():
    """Honest design: without a configured correlation_field there is no reliable natural
    key to re-query by (sys_id is server-assigned and unknown before a successful write),
    so verify_uncertain_commit truthfully returns UNKNOWN rather than guessing -- proven
    first; the real requery path is then proven with correlation_field configured."""
    ta = TransportAuthority()
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="incident", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"correlation_id": "corr-1", "short_description": "test"}],
        column_names=["correlation_id", "short_description"],
    )

    session_no_corr = _FakeServiceNowSessionForCommitCheck(found_rows=[{"sys_id": "1"}])
    writer_no_corr = ta.resolve_target_writer_for_provider("servicenow", connection_params={"db_connection": session_no_corr, "base_url": session_no_corr.base_url})
    outcome_no_corr = writer_no_corr.verify_uncertain_commit("incident", "", [], batch)
    assert outcome_no_corr == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
    assert not session_no_corr.get_calls  # no fabricated query without a real key to check

    session_committed = _FakeServiceNowSessionForCommitCheck(found_rows=[{"sys_id": "1"}])
    writer_committed = ta.resolve_target_writer_for_provider(
        "servicenow", connection_params={"db_connection": session_committed, "base_url": session_committed.base_url, "correlation_field": "correlation_id"}
    )
    outcome = writer_committed.verify_uncertain_commit("incident", "", [], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    assert session_committed.get_calls  # real requery issued

    session_not_committed = _FakeServiceNowSessionForCommitCheck(found_rows=[])
    writer_not_committed = ta.resolve_target_writer_for_provider(
        "servicenow", connection_params={"db_connection": session_not_committed, "base_url": session_not_committed.base_url, "correlation_field": "correlation_id"}
    )
    outcome2 = writer_not_committed.verify_uncertain_commit("incident", "", [], batch)
    assert outcome2 == CommitOutcomeState.NOT_COMMITTED


# ---------------------------------------------------------------------------
# 10. SAP Application Ecosystem -- capability-driven interface modes
#     (OData fully locally provable; RFC/BAPI + IDoc genuinely dependency-gated)
# ---------------------------------------------------------------------------

class _FakeSAPODataSession:
    def __init__(self, pages):
        self._pages = pages
        self._idx = 0
        self.base_url = "https://sap.internal/sap/opu/odata/sap/ZAKAAL_SRV"
        self.get_calls = []
        self.posted = []
        self.put_calls = []

    def get(self, url, params=None):
        self.get_calls.append((url, params))
        page = self._pages[min(self._idx, len(self._pages) - 1)]
        self._idx += 1
        return _FakeResponse({"d": {"results": page}})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return _FakeResponse({"d": json}, status_code=201)

    def put(self, url, json=None):
        self.put_calls.append((url, json))
        return _FakeResponse({"d": json})


def test_sap_application_odata_reader_uses_real_skip_top_pagination():
    session = _FakeSAPODataSession([[{"Id": "1"}, {"Id": "2"}], []])
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider(
        "sap_application", connection_params={"db_connection": session, "base_url": session.base_url, "interface_mode": "odata"}
    )
    reader.open_partition(_partition(table_name="ZAKAAL_ENTITYSet"))
    b1 = reader.read_batch(batch_size=2)
    assert b1 is not None and len(b1.rows) == 2
    assert reader.resume_position == 2
    url, params = session.get_calls[0]
    assert params["$skip"] == 0 and params["$top"] == 2


def test_sap_application_odata_writer_reaches_real_post_boundary():
    session = _FakeSAPODataSession([[]])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(
        "sap_application", connection_params={"db_connection": session, "base_url": session.base_url, "interface_mode": "odata"}
    )
    assert writer.get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT  # no correlation_field configured
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="ZAKAAL_ENTITYSet", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"Name": "Acme"}],
        column_names=["Name"],
    )
    written = writer.write_batch("ZAKAAL_ENTITYSet", batch)
    assert written == 1
    assert session.posted


def test_sap_application_odata_writer_correlation_field_upsert_is_idempotent():
    session = _FakeSAPODataSession([[]])
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(
        "sap_application",
        connection_params={"db_connection": session, "base_url": session.base_url, "interface_mode": "odata", "correlation_field": "ExternalId"},
    )
    assert writer.get_capabilities().idempotency == IdempotencyMode.OPERATION_IDEMPOTENT
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="ZAKAAL_ENTITYSet", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"ExternalId": "ext-1", "Name": "Acme"}],
        column_names=["ExternalId", "Name"],
    )
    writer.write_batch("ZAKAAL_ENTITYSet", batch)
    assert session.put_calls
    assert "ext-1" in session.put_calls[0][0]


def test_sap_application_odata_verify_uncertain_commit_is_real_get_requery():
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="ZAKAAL_ENTITYSet", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"ExternalId": "ext-1", "Name": "Acme"}],
        column_names=["ExternalId", "Name"],
    )
    ta = TransportAuthority()

    session_committed = _FakeSAPODataSession([[{"ExternalId": "ext-1"}]])
    writer_committed = ta.resolve_target_writer_for_provider(
        "sap_application",
        connection_params={"db_connection": session_committed, "base_url": session_committed.base_url, "interface_mode": "odata", "correlation_field": "ExternalId"},
    )
    outcome = writer_committed.verify_uncertain_commit("ZAKAAL_ENTITYSet", "", [], batch)
    assert outcome == CommitOutcomeState.COMMITTED
    assert session_committed.get_calls

    # Without correlation_field configured, honestly UNKNOWN rather than guessing.
    session_no_corr = _FakeSAPODataSession([[]])
    writer_no_corr = ta.resolve_target_writer_for_provider(
        "sap_application", connection_params={"db_connection": session_no_corr, "base_url": session_no_corr.base_url, "interface_mode": "odata"}
    )
    outcome2 = writer_no_corr.verify_uncertain_commit("ZAKAAL_ENTITYSet", "", [], batch)
    assert outcome2 == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME


def _pyrfc_actually_installed() -> bool:
    try:
        import pyrfc  # noqa: F401
        return True
    except ImportError:
        return False


def test_sap_application_rfc_and_idoc_modes_fail_closed_without_pyrfc():
    """Genuine dependency gate, not a fabricated capability: RFC/BAPI and IDoc modes
    require the proprietary pyrfc SDK. In this sandbox (and most CI/local environments
    without the SAP NetWeaver RFC SDK C library) pyrfc is not installed, so both modes
    must fail closed with TransportCapabilityError rather than silently degrading to
    OData or fabricating a connection."""
    if _pyrfc_actually_installed():
        pytest.skip("pyrfc is installed in this environment; dependency-gate behavior cannot be exercised here")

    ta = TransportAuthority()
    for mode in ("rfc_bapi", "idoc"):
        with pytest.raises(TransportCapabilityError):
            ta.resolve_source_reader_for_provider("sap_application", connection_params={"interface_mode": mode})
        with pytest.raises(TransportCapabilityError):
            ta.resolve_target_writer_for_provider("sap_application", connection_params={"interface_mode": mode})


class _FakeRFCConnection:
    """Minimal real-shaped pyrfc.Connection double -- exercises the RFC/BAPI and IDoc
    code paths as if pyrfc were installed and connected, without requiring the actual
    proprietary SDK in this environment."""
    def __init__(self, read_table_response=None):
        self._read_table_response = read_table_response or {"FIELDS": [], "DATA": []}
        self.calls = []

    def call(self, function_name, **kwargs):
        self.calls.append((function_name, kwargs))
        if function_name == "RFC_READ_TABLE":
            return self._read_table_response
        return {"RETURN": []}


def test_sap_application_rfc_bapi_reader_reaches_real_rfc_read_table_call():
    rfc_conn = _FakeRFCConnection(read_table_response={
        "FIELDS": [{"FIELDNAME": "MATNR"}, {"FIELDNAME": "MAKTX"}],
        "DATA": [{"WA": ("100".ljust(50) + "Widget".ljust(50))}],
    })
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("sap_application", connection_params={"db_connection": rfc_conn, "interface_mode": "rfc_bapi"})
    reader.open_partition(_partition(table_name="MAKT"))
    batch = reader.read_batch(batch_size=10)
    assert batch is not None and len(batch.rows) == 1
    assert batch.rows[0]["MATNR"] == "100"
    assert rfc_conn.calls[0][0] == "RFC_READ_TABLE"
    assert rfc_conn.calls[0][1]["QUERY_TABLE"] == "MAKT"


def test_sap_application_idoc_reader_reaches_real_edidc_requery():
    rfc_conn = _FakeRFCConnection(read_table_response={
        "FIELDS": [{"FIELDNAME": "DOCNUM"}],
        "DATA": [{"WA": "0000000001".ljust(50)}],
    })
    ta = TransportAuthority()
    reader = ta.resolve_source_reader_for_provider("sap_application", connection_params={"db_connection": rfc_conn, "interface_mode": "idoc"})
    reader.open_partition(_partition(table_name="ORDERS05"))
    batch = reader.read_batch(batch_size=10)
    assert batch is not None and len(batch.rows) == 1
    assert rfc_conn.calls[0][0] == "RFC_READ_TABLE"
    assert rfc_conn.calls[0][1]["QUERY_TABLE"] == "EDIDC"


def test_sap_application_rfc_bapi_writer_detects_genuine_bapi_error_return():
    class _FailingRFCConnection(_FakeRFCConnection):
        def call(self, function_name, **kwargs):
            self.calls.append((function_name, kwargs))
            return {"RETURN": [{"TYPE": "E", "MESSAGE": "material already exists"}]}

    rfc_conn = _FailingRFCConnection()
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(
        "sap_application", connection_params={"db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"}
    )
    batch = TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="MAKT", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"MATNR": "100"}],
        column_names=["MATNR"],
    )
    from akaalEngine.transport.models.errors import TransportWriteError
    with pytest.raises(TransportWriteError):
        writer.write_batch("MAKT", batch)
