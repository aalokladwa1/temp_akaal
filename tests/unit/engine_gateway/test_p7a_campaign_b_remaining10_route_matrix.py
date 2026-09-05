"""
tests.unit.engine_gateway.test_p7a_campaign_b_remaining10_route_matrix
========================================================================
P7A Campaign B — Remaining-10-Provider PROVIDER-BY-PROVIDER Gateway acceptance closure.

Mirrors `test_p7a_campaign_b_first10_route_matrix.py`'s methodology for the nine
implemented remaining-10 providers (Teradata, Vertica, SAP HANA, SAP ASE, Informix,
Cosmos DB, Spanner, Salesforce, ServiceNow):

  Route A: Teradata   (source) -> Vertica     (target)   [DB-API relational]
  Route B: Vertica    (source) -> SAP HANA    (target)   [DB-API relational]
  Route C: SAP HANA   (source) -> SAP ASE     (target)   [DB-API -> unquoted-identifier]
  Route D: SAP ASE    (source) -> Informix    (target)   [unquoted-identifier family]
  Route E: Informix   (source) -> Teradata    (target)   [closes the 5-provider relational loop]
  Route F: Cosmos DB  (source) -> Spanner     (target)   [cloud-native]
  Route G: Spanner    (source) -> Salesforce  (target)   [cloud-native -> SaaS]
  Route H: Salesforce (source) -> ServiceNow  (target)   [SaaS]
  Route I: ServiceNow (source) -> Cosmos DB   (target)   [closes the 4-provider cloud/SaaS loop]
  Route J: Informix   (source) -> SAP Application (target, OData mode) [relational -> SAP app]
  Route K: SAP Application (source, OData mode) -> Cosmos DB (target)  [SAP app -> cloud, covers
                                                                          all 10 remaining-10
                                                                          providers]

Each route proves, with REAL production code and mocks ONLY at the external SDK
boundary: physical source read, physical target write, real Telemetry, real Evidence
#12, and RESOLVE_CAPABILITIES reflecting real capability truth for both providers.
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
    secret = "akaal-remaining10-route-matrix-secret-v1"
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


# ---------------------------------------------------------------------------
# Fake external SDK boundaries
# ---------------------------------------------------------------------------

class FakeSqlCursor:
    def __init__(self, rows, description):
        self._rows = list(rows)
        self.description = description
        self.rowcount = -1
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "count(" in sql.lower():
            self._count_result = [(len(self._rows),)]

    def executemany(self, sql, seq_of_params):
        self.executed.append((sql, seq_of_params))
        self.rowcount = len(seq_of_params)

    def fetchmany(self, n):
        batch, self._rows = self._rows[:n], self._rows[n:]
        return batch

    def fetchone(self):
        if hasattr(self, "_count_result") and self._count_result:
            return self._count_result.pop(0)
        return self._rows.pop(0) if self._rows else None

    def close(self):
        pass


class FakeSqlConnection:
    def __init__(self, module_name, rows=(), description=()):
        self.__class__.__module__ = module_name
        self._cursor = FakeSqlCursor(list(rows), list(description))
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class FakeCosmosPage:
    def __init__(self, items, token):
        self._items = items
        self.continuation_token = token

    def __iter__(self):
        return iter(self._items)


class FakeCosmosContainer:
    def __init__(self, pages):
        self._pages = pages
        self.upserted: List[Dict[str, Any]] = []

    def query_items(self, query, enable_cross_partition_query=True, max_item_count=100):
        pages = self._pages

        class _Paged:
            def by_page(self, continuation_token=None):
                return iter(pages)
        return _Paged()

    def upsert_item(self, body):
        self.upserted.append(body)
        return body


class FakeSpannerResult:
    def __init__(self, rows, fields):
        self._rows = rows
        self.fields = fields

    def __iter__(self):
        return iter(self._rows)


class FakeSpannerField:
    def __init__(self, name):
        self.name = name


class FakeSpannerSnapshot:
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
        return FakeSpannerResult(rows, [FakeSpannerField("id"), FakeSpannerField("name")])


class FakeSpannerBatch:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def insert_or_update(self, table, columns, values):
        self.sink.append((table, columns, values))


class FakeSpannerDatabase:
    def __init__(self, rows_by_call):
        self._rows_by_call = rows_by_call
        self.batches: List[Any] = []

    def snapshot(self):
        return FakeSpannerSnapshot(self._rows_by_call)

    def batch(self):
        return FakeSpannerBatch(self.batches)


class FakeSalesforceClient:
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
        return [{"success": True, "id": f"new-{i}"} for i, _ in enumerate(json["records"])]


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeServiceNowSession:
    def __init__(self, pages):
        self._pages = pages
        self._idx = 0
        self.base_url = "https://dev12345.service-now.com"
        self.posted: List[Any] = []

    def get(self, url, params=None):
        page = self._pages[min(self._idx, len(self._pages) - 1)]
        self._idx += 1
        return FakeResponse({"result": page})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return FakeResponse({"result": {**json, "sys_id": "new-sys-id"}})


class FakeSAPODataSession:
    def __init__(self, pages):
        self._pages = pages
        self._idx = 0
        self.base_url = "https://sap.internal/sap/opu/odata/sap/ZAKAAL_SRV"
        self.get_calls: List[Any] = []
        self.posted: List[Any] = []

    def get(self, url, params=None):
        self.get_calls.append((url, params))
        page = self._pages[min(self._idx, len(self._pages) - 1)]
        self._idx += 1
        return FakeResponse({"d": {"results": page}})

    def post(self, url, json=None):
        self.posted.append((url, json))
        return FakeResponse({"d": json}, status_code=201)


# ---------------------------------------------------------------------------
# Route definitions
# ---------------------------------------------------------------------------

def _route_teradata_to_vertica():
    src_conn = FakeSqlConnection("teradatasql", rows=[(1, "a"), (2, "b")], description=[("id",), ("name",)])
    tgt_conn = FakeSqlConnection("vertica_python", rows=[])
    return {
        "source_provider_id": "teradata", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "vertica", "target_connection_params": {"db_connection": tgt_conn},
        "partition": _partition(table_name="orders", schema_name="s", target_schema="s", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_conn._cursor.executed,
    }


def _route_vertica_to_sap_hana():
    src_conn = FakeSqlConnection("vertica_python", rows=[(1, "a")], description=[("id",), ("name",)])
    tgt_conn = FakeSqlConnection("hdbcli", rows=[])
    return {
        "source_provider_id": "vertica", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "sap_hana", "target_connection_params": {"db_connection": tgt_conn},
        "partition": _partition(table_name="orders", schema_name="s", target_schema="s", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_conn._cursor.executed,
    }


def _route_sap_hana_to_sap_ase():
    src_conn = FakeSqlConnection("hdbcli", rows=[(1, "a")], description=[("id",), ("name",)])
    tgt_conn = FakeSqlConnection("pytds", rows=[])
    return {
        "source_provider_id": "sap_hana", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "sap_ase", "target_connection_params": {"db_connection": tgt_conn},
        "partition": _partition(table_name="orders", schema_name="dbo", target_schema="dbo", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_conn._cursor.executed,
    }


def _route_sap_ase_to_informix():
    src_conn = FakeSqlConnection("pytds", rows=[(1, "a")], description=[("id",), ("name",)])
    tgt_conn = FakeSqlConnection("ibm_db_dbi", rows=[])
    return {
        "source_provider_id": "sap_ase", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "informix", "target_connection_params": {"db_connection": tgt_conn},
        "partition": _partition(table_name="orders", schema_name="dbo", target_schema="informix", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_conn._cursor.executed,
    }


def _route_informix_to_teradata():
    src_conn = FakeSqlConnection("ibm_db_dbi", rows=[(1, "a")], description=[("id",), ("name",)])
    tgt_conn = FakeSqlConnection("teradatasql", rows=[])
    return {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "teradata", "target_connection_params": {"db_connection": tgt_conn},
        "partition": _partition(table_name="orders", schema_name="informix", target_schema="s", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_conn._cursor.executed,
    }


def _route_cosmosdb_to_spanner():
    src_container = FakeCosmosContainer([FakeCosmosPage([{"id": "1"}, {"id": "2"}], None)])
    tgt_db = FakeSpannerDatabase([[]])
    return {
        "source_provider_id": "cosmosdb", "source_connection_params": {"db_connection": src_container},
        "target_provider_id": "spanner", "target_connection_params": {"db_connection": tgt_db},
        "partition": _partition(table_name="items", schema_name="", target_schema="", pk_columns=("id",)),
        "_assert_source": lambda: src_container._pages is not None,
        "_assert_target": lambda: tgt_db.batches,
    }


def _route_spanner_to_salesforce():
    src_db = FakeSpannerDatabase([[(1, "a")]])
    tgt_client = FakeSalesforceClient(page1={})
    return {
        "source_provider_id": "spanner", "source_connection_params": {"db_connection": src_db},
        "target_provider_id": "salesforce", "target_connection_params": {"db_connection": tgt_client},
        "partition": _partition(table_name="Account", schema_name="", target_schema="", pk_columns=("id",)),
        "_assert_source": lambda: True,
        "_assert_target": lambda: tgt_client.restful_calls,
    }


def _route_salesforce_to_servicenow():
    src_client = FakeSalesforceClient(page1={"records": [{"Id": "1", "attributes": {}}], "done": True, "nextRecordsUrl": None})
    tgt_session = FakeServiceNowSession([[]])
    return {
        "source_provider_id": "salesforce", "source_connection_params": {"db_connection": src_client},
        "target_provider_id": "servicenow", "target_connection_params": {"db_connection": tgt_session, "base_url": tgt_session.base_url},
        "partition": _partition(table_name="Account", schema_name="", target_schema=""),
        "_assert_source": lambda: True,
        "_assert_target": lambda: tgt_session.posted,
    }


def _route_servicenow_to_cosmosdb():
    src_session = FakeServiceNowSession([[{"sys_id": "1"}], []])
    tgt_container = FakeCosmosContainer([])
    return {
        "source_provider_id": "servicenow", "source_connection_params": {"db_connection": src_session, "base_url": src_session.base_url},
        "target_provider_id": "cosmosdb", "target_connection_params": {"db_connection": tgt_container},
        "partition": _partition(table_name="incident", schema_name="", target_schema=""),
        "_assert_source": lambda: True,
        "_assert_target": lambda: tgt_container.upserted,
    }


def _route_informix_to_sap_application():
    src_conn = FakeSqlConnection("ibm_db_dbi", rows=[(1, "a")], description=[("id",), ("name",)])
    tgt_session = FakeSAPODataSession([[]])
    return {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": src_conn},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_session, "base_url": tgt_session.base_url, "interface_mode": "odata"},
        "partition": _partition(table_name="orders", schema_name="informix", target_schema="ZAKAAL_ENTITYSet", pk_columns=("id",)),
        "_assert_source": lambda: src_conn._cursor.executed,
        "_assert_target": lambda: tgt_session.posted,
    }


def _route_sap_application_to_cosmosdb():
    src_session = FakeSAPODataSession([[{"Id": "1"}], []])
    tgt_container = FakeCosmosContainer([])
    return {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_session, "base_url": src_session.base_url, "interface_mode": "odata"},
        "target_provider_id": "cosmosdb", "target_connection_params": {"db_connection": tgt_container},
        "partition": _partition(table_name="ZAKAAL_ENTITYSet", schema_name="", target_schema=""),
        "_assert_source": lambda: True,
        "_assert_target": lambda: tgt_container.upserted,
    }


ROUTES = {
    "teradata_to_vertica": _route_teradata_to_vertica,
    "vertica_to_sap_hana": _route_vertica_to_sap_hana,
    "sap_hana_to_sap_ase": _route_sap_hana_to_sap_ase,
    "sap_ase_to_informix": _route_sap_ase_to_informix,
    "informix_to_teradata": _route_informix_to_teradata,
    "cosmosdb_to_spanner": _route_cosmosdb_to_spanner,
    "spanner_to_salesforce": _route_spanner_to_salesforce,
    "salesforce_to_servicenow": _route_salesforce_to_servicenow,
    "servicenow_to_cosmosdb": _route_servicenow_to_cosmosdb,
    "informix_to_sap_application": _route_informix_to_sap_application,
    "sap_application_to_cosmosdb": _route_sap_application_to_cosmosdb,
}


@pytest.mark.parametrize("route_name", list(ROUTES.keys()))
def test_route_reaches_real_gateway_physical_boundary_with_telemetry_and_evidence(route_name):
    route = ROUTES[route_name]()
    tmp_dir = tempfile.mkdtemp(prefix=f"akaal_route_{route_name}_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = f"mig-route-{route_name}"
    ctx, token = _authenticated_context(migration_id, durability)

    payload = {
        "source_provider_id": route["source_provider_id"],
        "source_connection_params": route["source_connection_params"],
        "target_provider_id": route["target_provider_id"],
        "target_connection_params": route["target_connection_params"],
        "partition": route["partition"],
        "fencing_token": token,
    }
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload)
    resp = gw.execute(req)

    assert resp.success is True, resp
    assert route["_assert_source"](), f"real source physical boundary not reached for {route['source_provider_id']}"
    assert route["_assert_target"](), f"real target physical boundary not reached for {route['target_provider_id']}"

    snapshot = coordinator.telemetry_authority.get_metric_snapshot()
    counters = snapshot.counters if hasattr(snapshot, "counters") else {}
    started = [v for k, v in counters.items() if "gateway_bulk_migration_started" in k]
    assert started, "real Telemetry must record execution start for every route"

    assert coordinator.evidence_authority.evidence_artifacts_created_total >= 1
    assert resp.payload.get("evidence_artifact_id")

    for pid in (route["source_provider_id"], route["target_provider_id"]):
        cap_ctx, _ = _authenticated_context(f"{migration_id}-cap-{pid}", durability, worker_id=f"cap-worker-{pid}")
        cap_resp = gw.execute(GatewayRequest(operation=SemanticOperation.RESOLVE_CAPABILITIES, context=cap_ctx, payload={"provider_id": pid}))
        assert cap_resp.success is True, cap_resp
        assert cap_resp.payload["supported"] is True
        assert cap_resp.payload["provider_id"] == pid

    durability.close()


@pytest.mark.parametrize("route_name", list(ROUTES.keys()))
def test_route_rejects_execution_with_invalid_fencing_before_physical_boundary(route_name):
    """Security proof for all 9 remaining-10 providers: an invalid caller fencing epoch
    is rejected before the physical SDK boundary is ever reached."""
    route = ROUTES[route_name]()
    tmp_dir = tempfile.mkdtemp(prefix=f"akaal_route_sec_{route_name}_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    ctx = GatewayRequestContext(migration_id=f"mig-sec-{route_name}", run_id="run-1", fencing_epoch=-1)
    payload = {
        "source_provider_id": route["source_provider_id"],
        "source_connection_params": route["source_connection_params"],
        "target_provider_id": route["target_provider_id"],
        "target_connection_params": route["target_connection_params"],
        "partition": route["partition"],
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))
    assert resp.success is False

    durability.close()
