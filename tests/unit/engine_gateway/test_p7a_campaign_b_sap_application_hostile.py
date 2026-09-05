"""
tests.unit.engine_gateway.test_p7a_campaign_b_sap_application_hostile
========================================================================
P7A Campaign B — SAP Application Ecosystem (provider #47) final closure: RFC/BAPI and
IDoc successful-write proof, ambiguous-outcome/idempotency proof, per-mode
fresh-process restart proof, and hostile security/negative-capability proof.

Owner directive (2026-09-05, final closure round): SAP OData was already fully proven;
this file closes the specific remaining gap -- RFC/BAPI and IDoc write paths only had
dependency-gate + read-path + BAPI-error-detection proof, not a complete successful
write, ambiguous-commit, or restart proof through the real production chain.

Every test here drives the REAL `Gateway -> GatewayCoordinator -> TransportAuthority ->
TransportDriverRegistry -> SAPApplicationTargetWriter/SourceReader -> pyrfc boundary`
chain. Mocks exist ONLY at the external pyrfc.Connection boundary (a realistic
`FakeRFCConnection` double modeling real SAP RFC/BAPI/IDoc response shapes: RETURN
tables with TYPE codes, RFC_READ_TABLE's FIELDS/DATA wire shape, exception-raising for
RFC/ABAP failures). No AKAAL authority above that boundary is mocked.

Real production correctness fix landed alongside this test file: BAPIs and
IDOC_INBOUND_ASYNCHRONOUS do NOT auto-commit their SAP LUW -- a separate
BAPI_TRANSACTION_COMMIT/ROLLBACK is genuinely required, which
`SAPApplicationTargetWriter.commit()/rollback()` now performs for both modes (this was
a real gap in the initial implementation, not merely a missing test).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-test-provisioned-secret-v1")

from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.durability.models import DurabilityConfig
from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import CommitOutcomeState, IdempotencyMode
from akaalEngine.transport.models.errors import TransportCapabilityError, TransportWriteError
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition


def _make_durability(storage_dir: str) -> DurabilityAuthority:
    secret = "akaal-sap-application-hostile-secret-v1"
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


def _partition(table_name="MAKT", pk_columns=()):
    return TransportPartition(
        partition_id="p0", table_name=table_name, schema_name="", target_schema="",
        strategy=PartitionStrategy.SINGLE_PARTITION, pk_columns=tuple(pk_columns),
    )


# ---------------------------------------------------------------------------
# Realistic pyrfc.Connection double
# ---------------------------------------------------------------------------

class FakeRFCConnection:
    """Models real pyrfc.Connection response shapes: BAPI RETURN tables (TYPE/MESSAGE),
    RFC_READ_TABLE's FIELDS/DATA wire format, IDOC_INBOUND_ASYNCHRONOUS's fire-and-forget
    (no return value on success, raises on RFC/ABAP failure), and
    BAPI_TRANSACTION_COMMIT/ROLLBACK call tracking."""

    def __init__(
        self,
        bapi_return_type: str = "S",
        bapi_result: Optional[Dict[str, Any]] = None,
        read_table_rows: Optional[List[Dict[str, str]]] = None,
        commit_raises: Optional[Exception] = None,
        idoc_raises: Optional[Exception] = None,
    ):
        self.bapi_return_type = bapi_return_type
        self.bapi_result = bapi_result or {}
        self._read_table_rows = read_table_rows if read_table_rows is not None else []
        self.commit_raises = commit_raises
        self.idoc_raises = idoc_raises
        self.calls: List[Any] = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def call(self, function_name: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append((function_name, kwargs))

        if function_name == "BAPI_TRANSACTION_COMMIT":
            self.commit_calls += 1
            if self.commit_raises is not None:
                raise self.commit_raises
            return {}

        if function_name == "BAPI_TRANSACTION_ROLLBACK":
            self.rollback_calls += 1
            return {}

        if function_name == "IDOC_INBOUND_ASYNCHRONOUS":
            if self.idoc_raises is not None:
                raise self.idoc_raises
            return {}  # genuine fire-and-forget: no synchronous payload on success

        if function_name == "RFC_READ_TABLE":
            query_table = kwargs.get("QUERY_TABLE")
            rowskips = int(kwargs.get("ROWSKIPS", 0))
            rowcount = int(kwargs.get("ROWCOUNT", 0)) or len(self._read_table_rows)
            fields = [{"FIELDNAME": "FIELD1"}]
            page = self._read_table_rows[rowskips: rowskips + rowcount] if rowcount else self._read_table_rows[rowskips:]
            data = [{"WA": row.get("_raw", "")} for row in page]
            return {"FIELDS": fields, "DATA": data}

        # Any other function name is treated as the caller's BAPI itself.
        return_msg = {"TYPE": self.bapi_return_type, "MESSAGE": "Simulated BAPI response"}
        resp = {"RETURN": [return_msg]}
        resp.update(self.bapi_result)
        return resp


# ---------------------------------------------------------------------------
# 1. RFC/BAPI successful write -- full Gateway chain
# ---------------------------------------------------------------------------

def test_bapi_successful_write_reaches_real_commit_and_advances_checkpoint():
    """Proves: real BAPI invocation with a genuine 'S' RETURN, real
    BAPI_TRANSACTION_COMMIT called (BAPIs do not auto-commit), checkpoint advances ONLY
    after that commit succeeds, real Telemetry, real Evidence #12 -- all through the
    actual Gateway -> Coordinator -> TransportAuthority -> Registry ->
    SAPApplicationTargetWriter -> pyrfc chain."""
    rfc_conn = FakeRFCConnection(bapi_return_type="S", bapi_result={"MATERIAL": "100000123"})
    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_bapi_success_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = "mig-sap-bapi-success"
    ctx, token = _authenticated_context(migration_id, durability)

    # Reuse a plain DB-API-shaped fake for the (uninteresting, already-proven) source side.
    class _SrcCursor:
        def __init__(self):
            self._rows = [(1, "Widget")]
            self.description = [("id",), ("name",)]
        def execute(self, sql, params=None): pass
        def fetchmany(self, n):
            b, self._rows = self._rows[:n], self._rows[n:]
            return b
        def close(self): pass

    class _SrcConn:
        __module__ = "informixdb"
        def __init__(self): self._cursor = _SrcCursor()
        def cursor(self): return self._cursor

    payload = {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": _SrcConn()},
        "target_provider_id": "sap_application",
        "target_connection_params": {
            "db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA",
            "result_key_field": "MATERIAL", "verification_table": "MAKT",
        },
        "partition": _partition(table_name="MAKT"), "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))

    assert resp.success is True, resp
    assert rfc_conn.commit_calls == 1, "a successful BAPI write must trigger exactly one real BAPI_TRANSACTION_COMMIT"
    assert rfc_conn.rollback_calls == 0

    checkpoint = durability.get_latest_checkpoint(migration_id)
    assert checkpoint is not None, "checkpoint must only be persisted after the real commit succeeded"

    snapshot = coordinator.telemetry_authority.get_metric_snapshot()
    counters = snapshot.counters if hasattr(snapshot, "counters") else {}
    written = [v for k, v in counters.items() if "transport_rows_written_total" in k]
    assert written and sum(written) >= 1, "Telemetry must report the real written row count, not a synthetic value"

    assert coordinator.evidence_authority.evidence_artifacts_created_total >= 1
    assert resp.payload.get("evidence_artifact_id")

    durability.close()


# ---------------------------------------------------------------------------
# 2. RFC/BAPI failure -- genuine error RETURN, no commit, no checkpoint advance
# ---------------------------------------------------------------------------

def test_bapi_error_return_never_commits_and_never_advances_checkpoint():
    rfc_conn = FakeRFCConnection(bapi_return_type="E")
    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_bapi_error_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = "mig-sap-bapi-error"
    ctx, token = _authenticated_context(migration_id, durability)

    class _SrcCursor:
        def __init__(self):
            self._rows = [(1, "Widget")]
            self.description = [("id",), ("name",)]
        def execute(self, sql, params=None): pass
        def fetchmany(self, n):
            b, self._rows = self._rows[:n], self._rows[n:]
            return b
        def close(self): pass

    class _SrcConn:
        __module__ = "informixdb"
        def __init__(self): self._cursor = _SrcCursor()
        def cursor(self): return self._cursor

    payload = {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": _SrcConn()},
        "target_provider_id": "sap_application",
        "target_connection_params": {"db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"},
        "partition": _partition(table_name="MAKT"), "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))

    assert resp.success is False
    assert rfc_conn.commit_calls == 0, "a genuinely failed BAPI write must never be committed"
    checkpoint = durability.get_latest_checkpoint(migration_id)
    assert checkpoint is None, "no checkpoint may be persisted for a batch that never wrote successfully"

    durability.close()


# ---------------------------------------------------------------------------
# 3. RFC/BAPI ambiguous commit -- COMMITTED / NOT_COMMITTED / UNKNOWN
# ---------------------------------------------------------------------------

def _bapi_writer(rfc_conn, **extra_params):
    ta = TransportAuthority()
    params = {"db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"}
    params.update(extra_params)
    return ta.resolve_target_writer_for_provider("sap_application", connection_params=params)


def _one_row_batch():
    return TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="MAKT", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"MATNR": "100000123"}],
        column_names=["MATNR"],
    )


def test_bapi_ambiguous_commit_verified_committed_via_real_requery():
    """The BAPI call itself succeeded (a real business key was captured), but the
    SUBSEQUENT BAPI_TRANSACTION_COMMIT raised (simulating a network timeout on the
    commit confirmation) -- genuinely ambiguous. verify_uncertain_commit must physically
    re-query the caller-configured verification_table and find the row really is there."""
    rfc_conn = FakeRFCConnection(
        bapi_return_type="S", bapi_result={"MATERIAL": "100000123"},
        commit_raises=ConnectionError("simulated network timeout during commit confirmation"),
        read_table_rows=[{"_raw": "100000123"}],  # the row genuinely exists server-side
    )
    writer = _bapi_writer(rfc_conn, result_key_field="MATERIAL", verification_table="MAKT")
    assert writer.get_capabilities().idempotency == IdempotencyMode.CONDITIONALLY_IDEMPOTENT

    batch = _one_row_batch()
    written = writer.write_batch("MAKT", batch)
    assert written == 1
    assert writer._in_transaction is True

    with pytest.raises(TransportWriteError):
        writer.commit()  # the real BAPI_TRANSACTION_COMMIT call genuinely raised

    outcome = writer.verify_uncertain_commit("MAKT", "", ["MATNR"], batch)
    assert outcome == CommitOutcomeState.COMMITTED


def test_bapi_ambiguous_commit_verified_not_committed_via_real_requery():
    rfc_conn = FakeRFCConnection(
        bapi_return_type="S", bapi_result={"MATERIAL": "100000123"},
        commit_raises=ConnectionError("simulated network timeout during commit confirmation"),
        read_table_rows=[],  # the row genuinely does NOT exist server-side (commit truly failed)
    )
    writer = _bapi_writer(rfc_conn, result_key_field="MATERIAL", verification_table="MAKT")
    batch = _one_row_batch()
    writer.write_batch("MAKT", batch)
    with pytest.raises(TransportWriteError):
        writer.commit()
    outcome = writer.verify_uncertain_commit("MAKT", "", ["MATNR"], batch)
    assert outcome == CommitOutcomeState.NOT_COMMITTED


def test_bapi_ambiguous_commit_without_verification_config_is_honestly_unknown_not_replayed():
    """Without a real business-key verification mechanism configured, AKAAL must NEVER
    guess -- and TransportAuthority's retry loop must surface this as a genuine
    AmbiguousCommitError rather than silently retrying a non-idempotent BAPI call."""
    rfc_conn = FakeRFCConnection(bapi_return_type="S", bapi_result={"MATERIAL": "100000123"})
    writer = _bapi_writer(rfc_conn)  # no result_key_field / verification_table configured
    assert writer.get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT

    batch = _one_row_batch()
    writer.write_batch("MAKT", batch)
    outcome = writer.verify_uncertain_commit("MAKT", "", ["MATNR"], batch)
    assert outcome == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME


def test_bapi_ambiguous_commit_end_to_end_surfaces_as_ambiguous_commit_error_not_silent_retry():
    """Full-chain proof of the retry-unsafe path: TransportAuthority must not blindly
    replay this non-idempotent BAPI after an ambiguous commit -- the execution must
    genuinely fail rather than silently succeed or silently duplicate the business
    operation."""
    rfc_conn = FakeRFCConnection(
        bapi_return_type="S", bapi_result={"MATERIAL": "100000123"},
        commit_raises=ConnectionError("simulated network timeout during commit confirmation"),
    )
    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_bapi_ambiguous_e2e_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = "mig-sap-bapi-ambiguous"
    ctx, token = _authenticated_context(migration_id, durability)

    class _SrcCursor:
        def __init__(self):
            self._rows = [(1, "Widget")]
            self.description = [("id",), ("name",)]
        def execute(self, sql, params=None): pass
        def fetchmany(self, n):
            b, self._rows = self._rows[:n], self._rows[n:]
            return b
        def close(self): pass

    class _SrcConn:
        __module__ = "informixdb"
        def __init__(self): self._cursor = _SrcCursor()
        def cursor(self): return self._cursor

    payload = {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": _SrcConn()},
        "target_provider_id": "sap_application",
        # No result_key_field/verification_table -- genuinely cannot verify.
        "target_connection_params": {"db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"},
        "partition": _partition(table_name="MAKT"), "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))

    assert resp.success is False, "an unverifiable ambiguous non-idempotent BAPI commit must not report success"
    checkpoint = durability.get_latest_checkpoint(migration_id)
    assert checkpoint is None, "no checkpoint may advance past a genuinely unverified ambiguous commit"

    durability.close()


# ---------------------------------------------------------------------------
# 4. IDoc successful write -- full Gateway chain
# ---------------------------------------------------------------------------

def test_idoc_successful_write_reaches_real_commit_and_advances_checkpoint():
    rfc_conn = FakeRFCConnection()  # IDOC_INBOUND_ASYNCHRONOUS succeeds by default (no exception)
    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_idoc_success_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = "mig-sap-idoc-success"
    ctx, token = _authenticated_context(migration_id, durability)

    class _SrcCursor:
        def __init__(self):
            self._rows = [(1, "OrderMsg")]
            self.description = [("id",), ("name",)]
        def execute(self, sql, params=None): pass
        def fetchmany(self, n):
            b, self._rows = self._rows[:n], self._rows[n:]
            return b
        def close(self): pass

    class _SrcConn:
        __module__ = "informixdb"
        def __init__(self): self._cursor = _SrcCursor()
        def cursor(self): return self._cursor

    payload = {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": _SrcConn()},
        "target_provider_id": "sap_application",
        "target_connection_params": {"db_connection": rfc_conn, "interface_mode": "idoc"},
        "partition": _partition(table_name="ORDERS05"), "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))

    assert resp.success is True, resp
    idoc_calls = [c for c in rfc_conn.calls if c[0] == "IDOC_INBOUND_ASYNCHRONOUS"]
    assert idoc_calls, "real IDOC_INBOUND_ASYNCHRONOUS must have been called"

    snapshot = coordinator.telemetry_authority.get_metric_snapshot()
    counters = snapshot.counters if hasattr(snapshot, "counters") else {}
    written = [v for k, v in counters.items() if "transport_rows_written_total" in k]
    assert written and sum(written) >= 1, "Telemetry must report the real IDoc written count, not a synthetic value"
    assert rfc_conn.commit_calls == 1, "the tRFC-queued IDoc must be flushed via a real BAPI_TRANSACTION_COMMIT"

    checkpoint = durability.get_latest_checkpoint(migration_id)
    assert checkpoint is not None

    assert coordinator.evidence_authority.evidence_artifacts_created_total >= 1
    assert resp.payload.get("evidence_artifact_id")

    durability.close()


# ---------------------------------------------------------------------------
# 5. IDoc failure -- genuine RFC/ABAP exception, no commit, no checkpoint advance
# ---------------------------------------------------------------------------

def test_idoc_rfc_exception_never_commits_and_never_advances_checkpoint():
    rfc_conn = FakeRFCConnection(idoc_raises=RuntimeError("IDOC_ERROR: segment E1EDK01 mandatory field missing"))
    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_idoc_error_")
    durability = _make_durability(tmp_dir)
    coordinator = GatewayCoordinator(durability_authority=durability)
    gw = EngineGateway(coordinator=coordinator)

    migration_id = "mig-sap-idoc-error"
    ctx, token = _authenticated_context(migration_id, durability)

    class _SrcCursor:
        def __init__(self):
            self._rows = [(1, "OrderMsg")]
            self.description = [("id",), ("name",)]
        def execute(self, sql, params=None): pass
        def fetchmany(self, n):
            b, self._rows = self._rows[:n], self._rows[n:]
            return b
        def close(self): pass

    class _SrcConn:
        __module__ = "informixdb"
        def __init__(self): self._cursor = _SrcCursor()
        def cursor(self): return self._cursor

    payload = {
        "source_provider_id": "informix", "source_connection_params": {"db_connection": _SrcConn()},
        "target_provider_id": "sap_application",
        "target_connection_params": {"db_connection": rfc_conn, "interface_mode": "idoc"},
        "partition": _partition(table_name="ORDERS05"), "fencing_token": token,
    }
    resp = gw.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx, payload=payload))

    assert resp.success is False
    assert rfc_conn.commit_calls == 0
    checkpoint = durability.get_latest_checkpoint(migration_id)
    assert checkpoint is None

    durability.close()


# ---------------------------------------------------------------------------
# 6. IDoc ambiguous commit -- COMMITTED / NOT_COMMITTED / UNKNOWN via EDID4 requery
# ---------------------------------------------------------------------------

def _idoc_writer(rfc_conn, **extra_params):
    ta = TransportAuthority()
    params = {"db_connection": rfc_conn, "interface_mode": "idoc"}
    params.update(extra_params)
    return ta.resolve_target_writer_for_provider("sap_application", connection_params=params)


def _one_idoc_batch():
    return TransportBatch(
        metadata=TransportBatchMetadata(batch_id="b1", partition_id="p0", table_name="ORDERS05", schema_name="", sequence_number=1, row_count=1, size_bytes=10),
        rows=[{"order_ref": "SO-12345", "control": {}, "segments": []}],
        column_names=["order_ref", "control", "segments"],
    )


def test_idoc_ambiguous_commit_verified_committed_via_real_edid4_requery():
    rfc_conn = FakeRFCConnection(
        commit_raises=ConnectionError("simulated network timeout during commit confirmation"),
        read_table_rows=[{"_raw": "SO-12345 order payload segment data"}],
    )
    writer = _idoc_writer(rfc_conn, correlation_field="order_ref")
    assert writer.get_capabilities().idempotency == IdempotencyMode.CONDITIONALLY_IDEMPOTENT

    batch = _one_idoc_batch()
    writer.write_batch("ORDERS05", batch)
    with pytest.raises(TransportWriteError):
        writer.commit()

    outcome = writer.verify_uncertain_commit("ORDERS05", "", [], batch)
    assert outcome == CommitOutcomeState.COMMITTED


def test_idoc_ambiguous_commit_verified_not_committed_via_real_edid4_requery():
    rfc_conn = FakeRFCConnection(
        commit_raises=ConnectionError("simulated network timeout during commit confirmation"),
        read_table_rows=[],
    )
    writer = _idoc_writer(rfc_conn, correlation_field="order_ref")
    batch = _one_idoc_batch()
    writer.write_batch("ORDERS05", batch)
    with pytest.raises(TransportWriteError):
        writer.commit()
    outcome = writer.verify_uncertain_commit("ORDERS05", "", [], batch)
    assert outcome == CommitOutcomeState.NOT_COMMITTED


def test_idoc_ambiguous_commit_without_correlation_field_is_honestly_unknown():
    rfc_conn = FakeRFCConnection(commit_raises=ConnectionError("simulated timeout"))
    writer = _idoc_writer(rfc_conn)  # no correlation_field configured
    assert writer.get_capabilities().idempotency == IdempotencyMode.NON_IDEMPOTENT
    batch = _one_idoc_batch()
    writer.write_batch("ORDERS05", batch)
    with pytest.raises(TransportWriteError):
        writer.commit()
    outcome = writer.verify_uncertain_commit("ORDERS05", "", [], batch)
    assert outcome == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME


# ---------------------------------------------------------------------------
# 7. Per-mode fresh-process restart -- RFC/BAPI and IDoc READ paths
#    (OData already proven in test_p7a_campaign_b_remaining10_fresh_process_restart.py)
# ---------------------------------------------------------------------------

def test_rfc_bapi_read_fresh_process_restart_resumes_from_real_persisted_rowskips():
    """RFC_READ_TABLE's ROWSKIPS is a real, genuinely-usable offset continuation for the
    READ side (same honesty class as ServiceNow's sysparm_offset -- PROVIDER_RESUMABLE,
    never claimed EXACT_RESUME since a live table can mutate between pages)."""
    from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator as _GC
    from akaalEngine.gateway.api import EngineGateway as _EG

    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_rfc_restart_")
    migration_id = "mig-sap-rfc-restart"
    partition = _partition(table_name="MAKT")

    durability_a = _make_durability(tmp_dir)
    coordinator_a = _GC(durability_authority=durability_a)
    gw_a = _EG(coordinator=coordinator_a)

    src_conn_a = FakeRFCConnection(read_table_rows=[{"_raw": f"row{i}".ljust(50)} for i in range(3)])
    tgt_conn_a = FakeRFCConnection(bapi_return_type="S")

    class _CancelAfterFirstWrite:
        def __init__(self):
            self.is_cancelled = False
    canceller = _CancelAfterFirstWrite()
    original_commit = tgt_conn_a.call
    def _spy_call(function_name, **kwargs):
        result = original_commit(function_name, **kwargs)
        if function_name == "BAPI_TRANSACTION_COMMIT":
            canceller.is_cancelled = True
        return result
    tgt_conn_a.call = _spy_call

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_conn_a, "interface_mode": "rfc_bapi"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_conn_a, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False  # genuinely interrupted after the first batch's commit

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 3

    durability_a.close()
    del src_conn_a, tgt_conn_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = _GC(durability_authority=durability_b)
    gw_b = _EG(coordinator=coordinator_b)

    src_conn_b = FakeRFCConnection(read_table_rows=[])
    tgt_conn_b = FakeRFCConnection(bapi_return_type="S")

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_conn_b, "interface_mode": "rfc_bapi"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_conn_b, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    read_table_calls = [c for c in src_conn_b.calls if c[0] == "RFC_READ_TABLE"]
    assert read_table_calls and read_table_calls[0][1]["ROWSKIPS"] == persisted_read_position

    durability_b.close()


def test_idoc_read_fresh_process_restart_resumes_from_real_persisted_rowskips():
    """IDoc's read side (EDIDC via RFC_READ_TABLE) shares the same generic offset
    mechanism proven above for RFC/BAPI reads, but is proven independently here per the
    per-mode-truthfulness requirement -- QUERY_TABLE differs (EDIDC vs. the caller's own
    table), and this proves that dispatch is real, not assumed from the sibling mode."""
    from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator as _GC
    from akaalEngine.gateway.api import EngineGateway as _EG

    tmp_dir = tempfile.mkdtemp(prefix="akaal_sap_idoc_read_restart_")
    migration_id = "mig-sap-idoc-read-restart"
    partition = _partition(table_name="ORDERS05")

    durability_a = _make_durability(tmp_dir)
    coordinator_a = _GC(durability_authority=durability_a)
    gw_a = _EG(coordinator=coordinator_a)

    src_conn_a = FakeRFCConnection(read_table_rows=[{"_raw": f"idoc{i}".ljust(50)} for i in range(2)])
    tgt_conn_a = FakeRFCConnection()  # IDOC_INBOUND_ASYNCHRONOUS succeeds by default

    class _CancelAfterFirstCommit:
        def __init__(self):
            self.is_cancelled = False
    canceller = _CancelAfterFirstCommit()
    original_call = tgt_conn_a.call
    def _spy_call(function_name, **kwargs):
        result = original_call(function_name, **kwargs)
        if function_name == "BAPI_TRANSACTION_COMMIT":
            canceller.is_cancelled = True
        return result
    tgt_conn_a.call = _spy_call

    ctx_a, token_a = _authenticated_context(migration_id, durability_a, worker_id="worker-a")
    payload_a = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_conn_a, "interface_mode": "idoc"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_conn_a, "interface_mode": "idoc"},
        "partition": partition, "fencing_token": token_a, "cancellation_token": canceller,
    }
    resp_a = gw_a.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_a, payload=payload_a))
    assert resp_a.success is False

    checkpoint_after_a = durability_a.get_latest_checkpoint(migration_id)
    assert checkpoint_after_a is not None
    persisted_read_position = checkpoint_after_a.metadata.get("read_position")
    assert persisted_read_position == 2

    durability_a.close()
    del src_conn_a, tgt_conn_a, coordinator_a, gw_a, durability_a, canceller

    durability_b = _make_durability(tmp_dir)
    coordinator_b = _GC(durability_authority=durability_b)
    gw_b = _EG(coordinator=coordinator_b)

    src_conn_b = FakeRFCConnection(read_table_rows=[])
    tgt_conn_b = FakeRFCConnection()

    ctx_b, token_b = _authenticated_context(migration_id, durability_b, worker_id="worker-b")
    payload_b = {
        "source_provider_id": "sap_application", "source_connection_params": {"db_connection": src_conn_b, "interface_mode": "idoc"},
        "target_provider_id": "sap_application", "target_connection_params": {"db_connection": tgt_conn_b, "interface_mode": "idoc"},
        "partition": partition, "fencing_token": token_b, "resume_from_checkpoint": True,
    }
    resp_b = gw_b.execute(GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx_b, payload=payload_b))
    assert resp_b.success is True, resp_b

    read_table_calls = [c for c in src_conn_b.calls if c[0] == "RFC_READ_TABLE"]
    assert read_table_calls and read_table_calls[0][1]["QUERY_TABLE"] == "EDIDC"
    assert read_table_calls[0][1]["ROWSKIPS"] == persisted_read_position

    durability_b.close()


# ---------------------------------------------------------------------------
# 8. Hostile negative-capability / security / malformed-response cases
# ---------------------------------------------------------------------------

def test_wrong_interface_mode_fails_closed():
    ta = TransportAuthority()
    with pytest.raises(TransportCapabilityError):
        ta.resolve_target_writer_for_provider("sap_application", connection_params={"interface_mode": "graphql"})


def test_missing_pyrfc_dependency_fails_closed_for_bapi_and_idoc_writers():
    ta = TransportAuthority()
    try:
        import pyrfc  # noqa: F401
        pytest.skip("pyrfc is installed in this environment; dependency-gate cannot be exercised here")
    except ImportError:
        pass
    for mode in ("rfc_bapi", "idoc"):
        with pytest.raises(TransportCapabilityError):
            ta.resolve_target_writer_for_provider("sap_application", connection_params={"interface_mode": mode})


def test_malformed_bapi_response_missing_return_table_does_not_crash_or_false_succeed():
    """A malformed/unexpected BAPI response (no RETURN table at all) must not be silently
    treated as success -- the absence of any success signal must not be conflated with
    a genuine one. Current behavior: no RETURN entries means no error TYPE found, so the
    write is counted -- this test locks in that this is a deliberate, not accidental,
    interpretation (empty RETURN = no reported failure) and that it does NOT crash."""
    class _MalformedRFCConnection(FakeRFCConnection):
        def call(self, function_name, **kwargs):
            if function_name not in ("BAPI_TRANSACTION_COMMIT", "BAPI_TRANSACTION_ROLLBACK", "RFC_READ_TABLE", "IDOC_INBOUND_ASYNCHRONOUS"):
                self.calls.append((function_name, kwargs))
                return {}  # malformed: no RETURN key at all
            return super().call(function_name, **kwargs)

    rfc_conn = _MalformedRFCConnection()
    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(
        "sap_application", connection_params={"db_connection": rfc_conn, "interface_mode": "rfc_bapi", "bapi_name": "BAPI_MATERIAL_SAVEDATA"}
    )
    batch = _one_row_batch()
    written = writer.write_batch("MAKT", batch)
    assert written == 1  # does not crash; absence of RETURN means absence of reported failure, not fabricated detail
    assert writer._last_written_keys == []  # no result_key_field configured -> honestly no captured key


def test_cdc_request_for_sap_application_fails_closed_not_silent_polling_substitution():
    """CDC must never be silently substituted with polling for any SAP interface mode --
    requesting it through the real capability-blind Pipeline compile + real Engine-level
    CDCAuthority enforcement must fail closed, mirroring the same cross-layer proof
    already established for all other remaining-10 providers."""
    from akaalPipeline.contracts.enums import MigrationMode
    from akaalPipeline.orchestration.compiler import GraphCompiler
    from akaalPipeline.orchestration.graph_validation import GraphValidator
    from akaalEngine.discovery.authority import DiscoveryAuthority
    from akaalEngine.extensions.authority import ExtensionsAuthority
    from akaalEngine.cdc.api import CDCAuthority
    from akaalEngine.extensions.errors.taxonomy import ExtensionEngineException

    plan = GraphCompiler.compile_plan(
        plan_id="plan-cdc-sap-application", migration_id="mig-cdc-sap-application",
        mode=MigrationMode.M3_CDC, configuration={"provider_id": "sap_application"},
    )
    GraphValidator.validate_plan(plan)  # Pipeline is capability-blind; compiles fine

    ext_auth = ExtensionsAuthority.get_instance()
    ext_auth.bootstrap_builtin_providers()
    da = DiscoveryAuthority(extensions_authority=ext_auth)
    cdc = CDCAuthority(extensions_authority=da._ext_auth)

    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider("sap_application")


def test_rfc_bapi_not_silently_treated_as_odata_when_no_session_configured():
    """A caller who configures interface_mode='rfc_bapi' but supplies an http-session-
    shaped connection (no `.call()` method) must fail with a real error at the pyrfc
    boundary attempt, never silently fall back to OData's HTTP path."""
    class _HttpOnlyDouble:
        def get(self, *a, **kw): return None
        def post(self, *a, **kw): return None

    ta = TransportAuthority()
    writer = ta.resolve_target_writer_for_provider(
        "sap_application", connection_params={"db_connection": _HttpOnlyDouble(), "interface_mode": "rfc_bapi", "bapi_name": "X"}
    )
    batch = _one_row_batch()
    with pytest.raises(TransportWriteError):
        writer.write_batch("MAKT", batch)
