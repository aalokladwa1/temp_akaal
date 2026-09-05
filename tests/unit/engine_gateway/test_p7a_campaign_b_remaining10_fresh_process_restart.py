"""
tests.unit.engine_gateway.test_p7a_campaign_b_remaining10_fresh_process_restart
===================================================================================
P7A Campaign B — Remaining-10-Provider fresh-process restart proof.

Mirrors the First-10 mandatory restart proof
(`test_p7a_campaign_b_first10_e2e_closure.py::test_fresh_process_restart_resumes_from_
real_persisted_checkpoint`) for ALL NINE implemented remaining-10 providers:
Teradata/Vertica/SAP HANA (SQL keyset EXACT_RESUME, GenericSQL-reuse family), SAP
ASE/Informix (SQL keyset EXACT_RESUME, standalone unquoted-identifier family), Spanner
(SQL keyset EXACT_RESUME, Mutation-API cloud-native family), Cosmos DB (server
continuation-token PROVIDER_RESUMABLE), Salesforce (nextRecordsUrl PROVIDER_RESUMABLE),
ServiceNow (sysparm_offset PROVIDER_RESUMABLE -- honestly NOT exact-resume: concurrent
inserts/deletes during a scan can shift offset-based results, same honesty class as the
First-10 ClickHouse/Couchbase offset drivers; this test proves the offset continuation
is genuinely recovered and reused, not that ServiceNow guarantees exact positional
resume under concurrent mutation).

Runtime A commits and durably checkpoints one real batch, is interrupted (simulating a
process crash), and is then fully disposed (reader/writer/coordinator/gateway/durability
all dropped). A BRAND NEW Runtime B (fresh GatewayCoordinator, fresh EngineGateway, fresh
provider-native reader constructed only from the persisted checkpoint) resumes and uses
the REAL continuation value recovered from durable storage -- not an in-memory object
carried over between runs.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Any, Dict, List

import pytest

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-test-provisioned-secret-v1")

from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.durability.models import DurabilityConfig
from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition


def _make_durability(storage_dir: str) -> DurabilityAuthority:
    secret = "akaal-remaining10-restart-secret-v1"
    fencing_key = hashlib.sha256(secret.encode("utf-8") + b":fencing").digest()
    journal_key = hashlib.sha256(secret.encode("utf-8") + b":journal").digest()
    return DurabilityAuthority(
        config=DurabilityConfig(storage_dir=storage_dir, fencing_signing_key=fencing_key, journal_anchor_key=journal_key)
    )


def _authenticated_context(migration_id, durability, run_id="run-1", worker_id="test-worker"):
    canonical_res = f"{migration_id}/{run_id}"
    token = durability.issue_fencing_token(canonical_res, worker_id)
    envelope = {
        "token_version": "1.0.0", "canonical_resource_id": canonical_res, "resource_id": canonical_res,
        "migration_id": migration_id, "run_id": run_id, "job_id": None, "worker_id": worker_id,
        "fencing_epoch": token.fencing_epoch, "epoch": token.fencing_epoch,
        "issued_at": token.issued_at, "signature": token.signature, "engine_signature": token.signature,
    }
    ctx = GatewayRequestContext(migration_id=migration_id, run_id=run_id, fencing_epoch=token.fencing_epoch, fencing_token_envelope=envelope)
    return ctx, token


def _partition(table_name, schema_name="", target_schema="", pk_columns=()):
    return TransportPartition(
        partition_id="p0", table_name=table_name, schema_name=schema_name,
        target_schema=target_schema, strategy=PartitionStrategy.SINGLE_PARTITION, pk_columns=tuple(pk_columns),
    )


class _CancelAfterFirstBatch:
    """Cooperative cancellation token that flips ON right after the first batch's target
    write completes -- simulates a real process interruption occurring between committing
    batch 1 and starting batch 2."""
    def __init__(self):
        self.is_cancelled = False

    def arm_after_executemany(self, cursor) -> None:
        original = cursor.executemany

        def _wrapped(sql, seq_of_params):
            result = original(sql, seq_of_params)
            self.is_cancelled = True
            return result

        cursor.executemany = _wrapped

    def arm_after_upsert(self, container) -> None:
        original = container.upsert_item

        def _wrapped(body):
            result = original(body)
            self.is_cancelled = True
            return result

        container.upsert_item = _wrapped


# ---------------------------------------------------------------------------
# Teradata (relational, SQL keyset EXACT_RESUME)
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
    def __init__(self, module_name, rows=(), description=()):
        self.__class__.__module__ = module_name
        self._cursor = _FakeSqlCursor(list(rows), list(description))
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


RELATIONAL_FAMILY_MODULE = {
    "teradata": "teradatasql", "vertica": "vertica_python", "sap_hana": "hdbcli",
    "sap_ase": "pytds", "informix": "ibm_db_dbi",
}


@pytest.mark.parametrize("provider_id", list(RELATIONAL_FAMILY_MODULE.keys()))
def test_relational_family_fresh_process_restart_resumes_from_real_persisted_keyset(provider_id):
    """Covers all 5 relational providers: Teradata/Vertica/SAP HANA reuse
    GenericSQLSourceReader directly; SAP ASE/Informix use their standalone
    unquoted-identifier reader -- both real keyset paths are proven here."""
    module_name = RELATIONAL_FAMILY_MODULE[provider_id]
    tmp_dir = tempfile.mkdtemp(prefix=f"akaal_remaining10_restart_{provider_id}_")
    migration_id = f"mig-restart-{provider_id}-1"
    partition = _partition(table_name="orders", schema_name="s", target_schema="s", pk_columns=("id",))

    # ---- Runtime A: reads/writes one batch, then is interrupted ----
    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    src_conn_a = _FakeSqlConnection(module_name, rows=[(1, "a"), (2, "b"), (3, "c")], description=[("id",), ("name",)])
    tgt_conn_a = _FakeSqlConnection(module_name, rows=[])
    canceller = _CancelAfterFirstBatch()
    canceller.arm_after_executemany(tgt_conn_a._cursor)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": provider_id, "source_connection_params": {"db_connection": src_conn_a},
        "target_provider_id": provider_id, "target_connection_params": {"db_connection": tgt_conn_a},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False  # genuinely interrupted, not a fabricated clean completion
    assert tgt_conn_a._cursor.executed  # the first batch's write DID happen before interruption

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 3, f"[{provider_id}] expected last-read PK value 3, got {persisted_read_position}"

    durability_a.close()
    del src_conn_a, tgt_conn_a, coordinator_a, gw_a, durability_a, canceller

    # ---- Runtime B: brand-new process-equivalent state, resumes from the SAME on-disk store ----
    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    src_conn_b = _FakeSqlConnection(module_name, rows=[], description=[("id",), ("name",)])
    tgt_conn_b = _FakeSqlConnection(module_name, rows=[])

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": provider_id, "source_connection_params": {"db_connection": src_conn_b},
        "target_provider_id": provider_id, "target_connection_params": {"db_connection": tgt_conn_b},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader issued a real "> ?" keyset filter
    # seeded with the value recovered from durable storage, not a hardcoded/in-memory value.
    executed_sql = src_conn_b._cursor.executed[0][0]
    executed_params = src_conn_b._cursor.executed[0][1]
    assert "> ?" in executed_sql, f"[{provider_id}] resumed query must use a real keyset filter: {executed_sql}"
    assert executed_params == (persisted_read_position,), f"[{provider_id}] resumed query must be seeded with the persisted checkpoint value: {executed_params}"

    durability_b.close()


# ---------------------------------------------------------------------------
# Cosmos DB (cloud-native, real server continuation token)
# ---------------------------------------------------------------------------

class _FakeCosmosPage:
    def __init__(self, items, token):
        self._items = items
        self.continuation_token = token

    def __iter__(self):
        return iter(self._items)


class _FakeCosmosContainer:
    def __init__(self, pages):
        self._pages = pages
        self.upserted: List[Dict[str, Any]] = []
        self.last_continuation_requested = "UNSET"

    def query_items(self, query, enable_cross_partition_query=True, max_item_count=100):
        pages = self._pages
        outer = self

        class _Paged:
            def by_page(self, continuation_token=None):
                outer.last_continuation_requested = continuation_token
                return iter(pages)
        return _Paged()

    def upsert_item(self, body):
        self.upserted.append(body)
        return body


def test_cosmosdb_fresh_process_restart_resumes_from_real_persisted_continuation_token():
    tmp_dir = tempfile.mkdtemp(prefix="akaal_remaining10_restart_cosmosdb_")
    migration_id = "mig-restart-cosmosdb-1"
    partition = _partition(table_name="items", schema_name="", target_schema="")

    # ---- Runtime A ----
    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    src_container_a = _FakeCosmosContainer([_FakeCosmosPage([{"id": "1"}, {"id": "2"}], "server-token-xyz")])
    tgt_container_a = _FakeCosmosContainer([])
    canceller = _CancelAfterFirstBatch()
    canceller.arm_after_upsert(tgt_container_a)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "cosmosdb", "source_connection_params": {"db_connection": src_container_a},
        "target_provider_id": "cosmosdb", "target_connection_params": {"db_connection": tgt_container_a},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False
    assert len(tgt_container_a.upserted) == 2

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    assert checkpoint_after_a.metadata.get("read_position") == "server-token-xyz"

    durability_a.close()
    del src_container_a, tgt_container_a, coordinator_a, gw_a, durability_a, canceller

    # ---- Runtime B ----
    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    src_container_b = _FakeCosmosContainer([_FakeCosmosPage([{"id": "3"}], None)])
    tgt_container_b = _FakeCosmosContainer([])

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "cosmosdb", "source_connection_params": {"db_connection": src_container_b},
        "target_provider_id": "cosmosdb", "target_connection_params": {"db_connection": tgt_container_b},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader called by_page() with the REAL
    # continuation token persisted by Runtime A, recovered from durable storage.
    assert src_container_b.last_continuation_requested == "server-token-xyz"
    assert len(tgt_container_b.upserted) == 1

    durability_b.close()


# ---------------------------------------------------------------------------
# Spanner (cloud-native, real SQL keyset via Mutation-API writer)
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


class _FakeSpannerSnapshot:
    def __init__(self, rows_by_call):
        self._rows_by_call = rows_by_call
        self._idx = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute_sql(self, sql, params=None, param_types=None):
        rows = self._rows_by_call[min(self._idx, len(self._rows_by_call) - 1)]
        self._idx += 1
        self.last_params = params
        return _FakeSpannerResult(rows, [_FakeSpannerField("id"), _FakeSpannerField("name")])


class _FakeSpannerBatch:
    def __init__(self, sink, on_after=None):
        self.sink = sink
        self.on_after = on_after

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def insert_or_update(self, table, columns, values):
        self.sink.append((table, columns, values))
        if self.on_after:
            self.on_after()


class _FakeSpannerDatabase:
    def __init__(self, rows_by_call):
        self._snap = _FakeSpannerSnapshot(rows_by_call)
        self.batches = []
        self.on_after_write = None

    def snapshot(self):
        return self._snap

    def batch(self):
        return _FakeSpannerBatch(self.batches, on_after=self.on_after_write)


def test_spanner_fresh_process_restart_resumes_from_real_persisted_keyset():
    tmp_dir = tempfile.mkdtemp(prefix="akaal_remaining10_restart_spanner_")
    migration_id = "mig-restart-spanner-1"
    partition = _partition(table_name="orders", pk_columns=("id",))

    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    src_db_a = _FakeSpannerDatabase([[(1, "a"), (2, "b"), (3, "c")]])
    tgt_db_a = _FakeSpannerDatabase([[]])
    canceller = _CancelAfterFirstBatch()
    tgt_db_a.on_after_write = lambda: setattr(canceller, "is_cancelled", True)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "spanner", "source_connection_params": {"db_connection": src_db_a},
        "target_provider_id": "spanner", "target_connection_params": {"db_connection": tgt_db_a},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False
    assert tgt_db_a.batches

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 3

    durability_a.close()
    del src_db_a, tgt_db_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    src_db_b = _FakeSpannerDatabase([[]])
    tgt_db_b = _FakeSpannerDatabase([[]])

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "spanner", "source_connection_params": {"db_connection": src_db_b},
        "target_provider_id": "spanner", "target_connection_params": {"db_connection": tgt_db_b},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader issued a real "@last_key" keyset
    # parameter seeded with the value recovered from durable storage.
    assert src_db_b._snap.last_params is not None
    assert src_db_b._snap.last_params.get("last_key") == persisted_read_position

    durability_b.close()


# ---------------------------------------------------------------------------
# Salesforce (SaaS, real nextRecordsUrl continuation)
# ---------------------------------------------------------------------------

class _FakeSalesforceRestartClient:
    def __init__(self, page1, page2=None):
        self._page1 = page1
        self._page2 = page2
        self.query_more_calls = []
        self.restful_calls = []

    def query(self, soql):
        return self._page1

    def query_more(self, url, identifier_is_url=True):
        self.query_more_calls.append(url)
        return self._page2

    def restful(self, path, method="GET", json=None):
        self.restful_calls.append((path, method, json))
        return [{"success": True, "id": f"new-{i}"} for i, _ in enumerate(json["records"])]


def test_salesforce_fresh_process_restart_resumes_from_real_persisted_next_records_url():
    tmp_dir = tempfile.mkdtemp(prefix="akaal_remaining10_restart_salesforce_")
    migration_id = "mig-restart-salesforce-1"
    partition = _partition(table_name="Account")

    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    page1 = {"records": [{"Id": "1", "attributes": {}}, {"Id": "2", "attributes": {}}], "done": False, "nextRecordsUrl": "/services/data/v58.0/query/01g-2000"}
    src_client_a = _FakeSalesforceRestartClient(page1)
    tgt_client_a = _FakeSalesforceRestartClient(page1={})
    canceller = _CancelAfterFirstBatch()

    def _arm_after_restful(client):
        original = client.restful
        def _wrapped(path, method="GET", json=None):
            result = original(path, method=method, json=json)
            canceller.is_cancelled = True
            return result
        client.restful = _wrapped
    _arm_after_restful(tgt_client_a)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "salesforce", "source_connection_params": {"db_connection": src_client_a},
        "target_provider_id": "salesforce", "target_connection_params": {"db_connection": tgt_client_a},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False
    assert tgt_client_a.restful_calls

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == "/services/data/v58.0/query/01g-2000"

    durability_a.close()
    del src_client_a, tgt_client_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    page2 = {"records": [{"Id": "3", "attributes": {}}], "done": True, "nextRecordsUrl": None}
    src_client_b = _FakeSalesforceRestartClient(page1=None, page2=page2)
    tgt_client_b = _FakeSalesforceRestartClient(page1={})

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "salesforce", "source_connection_params": {"db_connection": src_client_b},
        "target_provider_id": "salesforce", "target_connection_params": {"db_connection": tgt_client_b},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: query_more() was called with the REAL nextRecordsUrl
    # persisted by Runtime A, recovered from durable storage -- NOT a fresh query().
    assert src_client_b.query_more_calls == [persisted_read_position]

    durability_b.close()


# ---------------------------------------------------------------------------
# ServiceNow (SaaS, real sysparm_offset continuation -- honestly PROVIDER_RESUMABLE,
# never claimed EXACT_RESUME)
# ---------------------------------------------------------------------------

class _FakeServiceNowRestartResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeServiceNowRestartSession:
    def __init__(self, pages):
        self._pages = pages
        self._idx = 0
        self.base_url = "https://dev12345.service-now.com"
        self.get_calls = []
        self.posted = []

    def get(self, url, params=None):
        self.get_calls.append(params)
        page = self._pages[min(self._idx, len(self._pages) - 1)]
        self._idx += 1
        return _FakeServiceNowRestartResponse({"result": page})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return _FakeServiceNowRestartResponse({"result": {**json, "sys_id": "new-sys-id"}})


def test_servicenow_fresh_process_restart_resumes_from_real_persisted_offset():
    tmp_dir = tempfile.mkdtemp(prefix="akaal_remaining10_restart_servicenow_")
    migration_id = "mig-restart-servicenow-1"
    partition = _partition(table_name="incident")

    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    src_session_a = _FakeServiceNowRestartSession([[{"sys_id": "1"}, {"sys_id": "2"}, {"sys_id": "3"}]])
    tgt_session_a = _FakeServiceNowRestartSession([[]])
    canceller = _CancelAfterFirstBatch()

    def _arm_after_post(session):
        original = session.post
        def _wrapped(url, json=None):
            result = original(url, json=json)
            canceller.is_cancelled = True
            return result
        session.post = _wrapped
    _arm_after_post(tgt_session_a)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "servicenow", "source_connection_params": {"db_connection": src_session_a, "base_url": src_session_a.base_url},
        "target_provider_id": "servicenow", "target_connection_params": {"db_connection": tgt_session_a, "base_url": tgt_session_a.base_url},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False
    assert tgt_session_a.posted

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 3

    durability_a.close()
    del src_session_a, tgt_session_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    src_session_b = _FakeServiceNowRestartSession([[{"sys_id": "4"}]])
    tgt_session_b = _FakeServiceNowRestartSession([[]])

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "servicenow", "source_connection_params": {"db_connection": src_session_b, "base_url": src_session_b.base_url},
        "target_provider_id": "servicenow", "target_connection_params": {"db_connection": tgt_session_b, "base_url": tgt_session_b.base_url},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader issued a real sysparm_offset request
    # seeded with the value recovered from durable storage.
    assert src_session_b.get_calls[0]["sysparm_offset"] == persisted_read_position

    durability_b.close()


# ---------------------------------------------------------------------------
# SAP Application Ecosystem (OData mode -- real $skip continuation; RFC/BAPI and IDoc
# modes are genuinely dependency-gated on pyrfc, proven separately in
# test_p7a_campaign_b_remaining10_transport_dataplane.py, and are honestly excluded
# from this local restart proof since no live pyrfc runtime exists in this sandbox)
# ---------------------------------------------------------------------------

class _FakeSAPODataRestartResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSAPODataRestartSession:
    def __init__(self, pages):
        self._pages = pages
        self._idx = 0
        self.base_url = "https://sap.internal/sap/opu/odata/sap/ZAKAAL_SRV"
        self.get_calls = []
        self.posted = []

    def get(self, url, params=None):
        self.get_calls.append(params)
        page = self._pages[min(self._idx, len(self._pages) - 1)]
        self._idx += 1
        return _FakeSAPODataRestartResponse({"d": {"results": page}})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return _FakeSAPODataRestartResponse({"d": json}, status_code=201)


def test_sap_application_odata_fresh_process_restart_resumes_from_real_persisted_skip():
    tmp_dir = tempfile.mkdtemp(prefix="akaal_remaining10_restart_sap_application_")
    migration_id = "mig-restart-sap-application-1"
    partition = _partition(table_name="ZAKAAL_ENTITYSet")

    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    src_session_a = _FakeSAPODataRestartSession([[{"Id": "1"}, {"Id": "2"}, {"Id": "3"}]])
    tgt_session_a = _FakeSAPODataRestartSession([[]])
    canceller = _CancelAfterFirstBatch()

    def _arm_after_post(session):
        original = session.post
        def _wrapped(url, json=None):
            result = original(url, json=json)
            canceller.is_cancelled = True
            return result
        session.post = _wrapped
    _arm_after_post(tgt_session_a)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_session_a, "base_url": src_session_a.base_url, "interface_mode": "odata"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_session_a, "base_url": tgt_session_a.base_url, "interface_mode": "odata"},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False
    assert tgt_session_a.posted

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 3

    durability_a.close()
    del src_session_a, tgt_session_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    src_session_b = _FakeSAPODataRestartSession([[{"Id": "4"}]])
    tgt_session_b = _FakeSAPODataRestartSession([[]])

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_session_b, "base_url": src_session_b.base_url, "interface_mode": "odata"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_session_b, "base_url": tgt_session_b.base_url, "interface_mode": "odata"},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader issued a real $skip request seeded
    # with the value recovered from durable storage.
    assert src_session_b.get_calls[0]["$skip"] == persisted_read_position

    durability_b.close()
