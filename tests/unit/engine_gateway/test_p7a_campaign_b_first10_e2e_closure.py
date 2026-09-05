"""
tests.unit.engine_gateway.test_p7a_campaign_b_first10_e2e_closure
=====================================================================
P7A Campaign B — First-10-Provider FULL END-TO-END closure proof.

Exercises the REAL production chain:

    GatewayRequest (generic, provider-neutral payload)
      -> EngineGateway.execute()
      -> GatewayDispatcher.dispatch()
      -> GatewayCoordinator.orchestrate_bulk_migration()   [real, pre-existing]
      -> TransportAuthority.execute_partition_transport()  [real, pre-existing + hardened]
      -> TransportDriverRegistry.resolve_*_for_provider()   [added in the prior hardening pass]
      -> provider-native SourceReader/TargetWriter          [added in the prior hardening pass]
      -> mocked external SDK boundary ONLY

with REAL TelemetryAuthority (metrics registry), REAL EvidenceAuthority (artifact
creation), and a REAL SQLite-backed DurabilityAuthority (temp-directory-backed, real
fencing tokens, real checkpoint persistence) -- none of these are mocked or replaced.

Nothing above the external SDK boundary is faked: Gateway, coordinator,
TransportAuthority, registry, and provider driver classes are all real production code.
Fencing/security is fully real too (a genuine issued token + matching envelope) -- these
tests exercise check_fencing()'s real barrier rather than bypassing it.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Any, Dict, List

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
    secret = "akaal-first10-e2e-test-secret-v1"
    fencing_key = hashlib.sha256(secret.encode("utf-8") + b":fencing").digest()
    journal_key = hashlib.sha256(secret.encode("utf-8") + b":journal").digest()
    return DurabilityAuthority(
        config=DurabilityConfig(
            storage_dir=storage_dir,
            fencing_signing_key=fencing_key,
            journal_anchor_key=journal_key,
        )
    )


def _partition(table_name, schema_name="", target_schema="", pk_columns=()):
    return TransportPartition(
        partition_id="p0",
        table_name=table_name,
        schema_name=schema_name,
        target_schema=target_schema,
        strategy=PartitionStrategy.SINGLE_PARTITION,
        pk_columns=tuple(pk_columns),
    )


def _authenticated_context(migration_id, durability, run_id="run-1", worker_id="test-worker"):
    """Builds a REAL, fully-authenticated GatewayRequestContext: issues a genuine fencing
    token from the real DurabilityAuthority and constructs the matching envelope exactly
    as check_fencing() requires (mirrors test_engine_gateway_hostile_suite.py's
    make_context() helper) -- so these tests exercise the real security barrier rather
    than bypassing it. Returns (context, token)."""
    canonical_res = f"{migration_id}/{run_id}"
    token = durability.issue_fencing_token(canonical_res, worker_id)
    envelope = {
        "token_version": "1.0.0",
        "canonical_resource_id": canonical_res,
        "resource_id": canonical_res,
        "migration_id": migration_id,
        "run_id": run_id,
        "job_id": None,
        "worker_id": worker_id,
        "fencing_epoch": token.fencing_epoch,
        "epoch": token.fencing_epoch,
        "issued_at": token.issued_at,
        "signature": token.signature,
        "engine_signature": token.signature,
    }
    ctx = GatewayRequestContext(
        migration_id=migration_id,
        run_id=run_id,
        fencing_epoch=token.fencing_epoch,
        fencing_token_envelope=envelope,
    )
    return ctx, token


# ---------------------------------------------------------------------------
# Fake external SDK boundaries (DynamoDB source, Couchbase target) -- everything
# above these classes in the production chain is real.
# ---------------------------------------------------------------------------

class _FakeDynamoClient:
    def __init__(self, pages):
        self._pages = list(pages)
        self.scan_calls: List[Dict[str, Any]] = []

    def scan(self, **kwargs):
        self.scan_calls.append(kwargs)
        items, lek = self._pages.pop(0)
        resp = {"Items": items}
        if lek:
            resp["LastEvaluatedKey"] = lek
        return resp


class _FakeCouchbaseCollection:
    def __init__(self):
        self.upserts: Dict[str, Any] = {}

    def upsert(self, doc_id, value):
        self.upserts[doc_id] = value


class _FakeCouchbaseCluster:
    def __init__(self, collection):
        self._collection = collection

    def bucket(self, name):
        outer = self

        class _Bucket:
            def scope(self, scope_name):
                class _Scope:
                    def collection(_self, name):
                        return outer._collection
                return _Scope()
        return _Bucket()


def test_full_chain_dynamodb_source_to_couchbase_target_reaches_physical_boundary():
    """The canonical heterogeneous-route proof: a real GatewayRequest for
    EXECUTE_BULK_MIGRATION, carrying only provider_id + connection_params (no
    pre-built reader/writer), drives the REAL Gateway -> coordinator -> TransportAuthority
    -> registry -> DynamoDBSourceReader -> CouchbaseTargetWriter chain, with real
    Telemetry/Durability/Evidence authorities participating, down to the mocked
    boto3/Couchbase SDK calls."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_dur_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    dynamo_client = _FakeDynamoClient([([{"id": {"S": "1"}}, {"id": {"S": "2"}}], None)])
    collection = _FakeCouchbaseCollection()
    couchbase_cluster = _FakeCouchbaseCluster(collection)

    ctx, token = _authenticated_context("mig-e2e-1", durability)
    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))

    payload = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": couchbase_cluster, "bucket": "b1"},
        "partition": partition,
        "fencing_token": token,
    }
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload)

    resp = gw.execute(req)

    assert resp.success is True, resp
    assert resp.payload["status"] == "COMPLETED"
    assert dynamo_client.scan_calls, "real DynamoDB source scan() must have been reached"
    assert collection.upserts, "real Couchbase target upsert() must have been reached"
    assert set(collection.upserts.keys()) == {"1", "2"}

    # Real Durability participation: an actual checkpoint was persisted for this migration
    # (the final "COMPLETED" marker, since this run consumed the entire partition -- the
    # richer per-batch read_position/table_name metadata is proven separately by the
    # restart test below, which inspects the checkpoint state that exists BEFORE the
    # final completion marker is written).
    checkpoint = durability.get_latest_checkpoint("mig-e2e-1")
    assert checkpoint is not None
    assert checkpoint.status == "COMPLETED"

    durability.close()


def test_full_chain_evidence_artifact_reflects_real_execution():
    """Evidence #12 must receive a real artifact for this specific migration/run, not a
    synthetic placeholder -- proven via the real EvidenceAuthority the coordinator holds."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_dur_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    dynamo_client = _FakeDynamoClient([([{"id": {"S": "1"}}], None)])
    collection = _FakeCouchbaseCollection()
    couchbase_cluster = _FakeCouchbaseCluster(collection)

    ctx, token = _authenticated_context("mig-e2e-evidence", durability)
    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))
    payload = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": couchbase_cluster, "bucket": "b1"},
        "partition": partition,
        "fencing_token": token,
    }
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload)

    resp = gw.execute(req)
    assert resp.success is True, resp

    evidence_authority = coordinator.evidence_authority
    assert evidence_authority.evidence_artifacts_created_total >= 1
    assert resp.payload.get("evidence_artifact_id")

    durability.close()


def test_full_chain_telemetry_reflects_real_row_counts():
    """Telemetry must record the ACTUAL number of rows observed by this specific
    execution, never a synthetic/invented count."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_dur_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    dynamo_client = _FakeDynamoClient([([{"id": {"S": "1"}}, {"id": {"S": "2"}}, {"id": {"S": "3"}}], None)])
    collection = _FakeCouchbaseCollection()
    couchbase_cluster = _FakeCouchbaseCluster(collection)

    ctx, token = _authenticated_context("mig-e2e-telemetry", durability)
    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))
    payload = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": couchbase_cluster, "bucket": "b1"},
        "partition": partition,
        "fencing_token": token,
    }
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload)
    resp = gw.execute(req)
    assert resp.success is True, resp

    snapshot = coordinator.telemetry_authority.get_metric_snapshot()
    counters = snapshot.counters if hasattr(snapshot, "counters") else {}
    rows_read_metrics = [v for k, v in counters.items() if "transport_rows_read_total" in k]
    assert rows_read_metrics, "real per-execution row-count telemetry must have been recorded"
    assert sum(rows_read_metrics) == 3  # the REAL row count observed, not a fabricated value

    durability.close()


class _CancelAfterFirstBatch:
    """Cooperative cancellation token that flips ON right after the first batch's target
    write completes -- simulates a real process interruption (crash/SIGTERM) occurring
    between committing batch 1 and starting batch 2, WITHOUT needing execute_partition_transport
    itself to expose a 'stop after N batches' parameter it doesn't have."""
    def __init__(self):
        self.is_cancelled = False

    def arm_after(self, collection: "_FakeCouchbaseCollection") -> None:
        original_upsert = collection.upsert

        def _upsert_then_cancel(doc_id, value):
            original_upsert(doc_id, value)
            self.is_cancelled = True

        collection.upsert = _upsert_then_cancel


def test_fresh_process_restart_resumes_from_real_persisted_checkpoint():
    """The mandatory restart proof: Runtime A commits and durably checkpoints one real
    batch, then is interrupted (simulating a process crash) before the source is fully
    exhausted; Runtime A's reader/writer/coordinator/gateway are then fully disposed; a
    BRAND NEW Runtime B (fresh GatewayCoordinator, fresh EngineGateway, fresh
    DynamoDBSourceReader constructed only from the persisted checkpoint) resumes and reads
    the REAL LastEvaluatedKey recovered from durable storage -- not an in-memory object
    carried over between runs."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_restart_")
    migration_id = "mig-restart-1"
    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))

    # ---- Runtime A: commits one batch, then is interrupted ----
    durability_a = _make_durability(tmp_dir)
    coordinator_a = GatewayCoordinator(durability_authority=durability_a)
    gw_a = EngineGateway(coordinator=coordinator_a)

    page1_items = [{"id": {"S": "1"}}, {"id": {"S": "2"}}]
    dynamo_client_a = _FakeDynamoClient([(page1_items, {"id": {"S": "2"}})])  # LastEvaluatedKey present -> more pages genuinely exist
    collection_a = _FakeCouchbaseCollection()
    couchbase_cluster_a = _FakeCouchbaseCluster(collection_a)
    canceller = _CancelAfterFirstBatch()
    canceller.arm_after(collection_a)

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client_a},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": couchbase_cluster_a, "bucket": "b1"},
        "partition": partition,
        "fencing_token": token_a,
        "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    # Runtime A is genuinely interrupted -- the operation truthfully reports non-success
    # (a real process crash is not a "successful, completed" migration), but the FIRST
    # batch's work was already durably committed and checkpointed before the interruption.
    assert resp_a.success is False
    assert len(collection_a.upserts) == 2

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    assert checkpoint_after_a.metadata.get("read_position") == {"id": {"S": "2"}}

    # Full disposal -- Runtime A's client, writer, coordinator, and gateway are all dropped.
    durability_a.close()
    del dynamo_client_a, coordinator_a, gw_a, durability_a, canceller

    # ---- Runtime B: brand-new process-equivalent state ----
    durability_b = _make_durability(tmp_dir)  # reopens the SAME on-disk SQLite store
    coordinator_b = GatewayCoordinator(durability_authority=durability_b)
    gw_b = EngineGateway(coordinator=coordinator_b)

    page2_items = [{"id": {"S": "3"}}]
    dynamo_client_b = _FakeDynamoClient([(page2_items, None)])
    collection_b = _FakeCouchbaseCollection()
    couchbase_cluster_b = _FakeCouchbaseCluster(collection_b)

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client_b},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": couchbase_cluster_b, "bucket": "b1"},
        "partition": partition,
        "fencing_token": token_b,
        "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    # Real physical proof of resume: the fresh reader was opened with the REAL
    # LastEvaluatedKey persisted by Runtime A, recovered from durable storage in Runtime B.
    assert dynamo_client_b.scan_calls[0].get("ExclusiveStartKey") == {"id": {"S": "2"}}
    assert set(collection_b.upserts.keys()) == {"3"}

    durability_b.close()


def test_wrong_migration_checkpoint_does_not_leak_into_unrelated_migration():
    """A fresh migration_id with no prior checkpoint must not accidentally resume from
    another migration's persisted position -- checkpoint identity is migration_id-scoped."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_isolation_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))

    # Migration 1 is interrupted after its first batch and persists a real checkpoint with
    # a real continuation position (same cancel-after-first-batch technique as the restart test).
    dynamo_1 = _FakeDynamoClient([([{"id": {"S": "1"}}], {"id": {"S": "1"}})])
    collection_1 = _FakeCouchbaseCollection()
    canceller_1 = _CancelAfterFirstBatch()
    canceller_1.arm_after(collection_1)
    ctx1, token1 = _authenticated_context("mig-isolation-A", durability, worker_id="worker-1")
    payload1 = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_1},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": _FakeCouchbaseCluster(collection_1), "bucket": "b1"},
        "partition": partition,
        "fencing_token": token1,
        "cancellation_token": canceller_1,
    }
    resp1 = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx1, payload=payload1))
    assert resp1.success is False  # interrupted, but batch 1 was durably committed+checkpointed
    assert durability.get_latest_checkpoint("mig-isolation-A").metadata.get("read_position") == {"id": {"S": "1"}}

    # Migration 2 (a DIFFERENT migration_id) requests resume -- must find NO checkpoint of
    # its own and must NOT pick up migration 1's LastEvaluatedKey.
    dynamo_2 = _FakeDynamoClient([([{"id": {"S": "99"}}], None)])
    collection_2 = _FakeCouchbaseCollection()
    ctx2, token2 = _authenticated_context("mig-isolation-B", durability, worker_id="worker-2")
    payload2 = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_2},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": _FakeCouchbaseCluster(collection_2), "bucket": "b1"},
        "partition": partition,
        "fencing_token": token2,
        "resume_from_checkpoint": True,
    }
    resp2 = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx2, payload=payload2))
    assert resp2.success is True, resp2

    assert "ExclusiveStartKey" not in dynamo_2.scan_calls[0]

    durability.close()


def test_invalid_fencing_epoch_rejected_before_physical_execution():
    """A malformed/invalid caller-supplied fencing epoch must be rejected by the REAL
    check_fencing() barrier BEFORE any physical SDK call is reached -- security is not
    bypassable by supplying a valid provider_id."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_security_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    dynamo_client = _FakeDynamoClient([([{"id": {"S": "1"}}], None)])
    collection = _FakeCouchbaseCollection()

    ctx = GatewayRequestContext(migration_id="mig-security-1", run_id="run-1", fencing_epoch=-1)
    partition = _partition(table_name="Orders", schema_name="_default.orders", target_schema="_default.orders", pk_columns=("id",))
    payload = {
        "source_provider_id": "dynamodb",
        "source_connection_params": {"db_connection": dynamo_client},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": _FakeCouchbaseCluster(collection), "bucket": "b1"},
        "partition": partition,
    }
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload)

    resp = gw.execute(req)
    assert resp.success is False
    assert not dynamo_client.scan_calls, "physical SDK boundary must NOT be reached when fencing is rejected"
    assert not collection.upserts

    durability.close()


def test_unknown_provider_id_fails_closed_through_full_gateway_chain():
    """An unregistered provider_id supplied through the real Gateway chain must fail
    closed with a normalized failure, not silently succeed or crash uninformatively."""
    tmp_dir = tempfile.mkdtemp(prefix="akaal_e2e_unknown_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    ctx, token = _authenticated_context("mig-unknown-1", durability)
    partition = _partition(table_name="t")
    payload = {
        "source_provider_id": "totally-unknown-provider-xyz",
        "source_connection_params": {},
        "target_provider_id": "couchbase",
        "target_connection_params": {"db_connection": _FakeCouchbaseCluster(_FakeCouchbaseCollection()), "bucket": "b1"},
        "partition": partition,
        "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))
    assert resp.success is False

    durability.close()
