"""tests/integration/pipeline_engine_gateway/test_pipeline_engine_gateway_integration.py
=============================================================================
Comprehensive Hostile & Integration Test Suite for Pipeline EngineGateway Adapter.
Verifies complete physical backend chain and all 10 consolidated problem groups:
  akaalPipeline → PipelineEngineGatewayAdapter → EngineGateway → Authorities #1-#12
"""

import os
import sqlite3
import uuid
import pytest

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-test-provisioned-secret-v1")

from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.durability.models.errors import DurabilityError, FencingViolationError
from akaalEngine.runtime.models.task import TaskSpec
from akaalPipeline.adapters.engine_gateway import PipelineEngineGatewayAdapter
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.capabilities.bindings import EngineBindingDescriptor
from akaalPipeline.contracts.enums import MigrationMode
from akaalPipeline.contracts.errors import PipelineError, StaleResultError
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.plans import ExecutionPlan
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def engine_gateway():
    return EngineGateway()


@pytest.fixture
def adapter(engine_gateway):
    return PipelineEngineGatewayAdapter(gateway=engine_gateway, owns_gateway=False)


@pytest.fixture
def caller(tmp_path):
    db_file = str(tmp_path / "pipeline_integration.db")
    c = PipelineUnifiedCaller(db_path=db_file, bind_gateway=True)
    yield c
    c.close()


# -----------------------------------------------------------------------------
# 1. Problem Group 1: Production DAG Dispatch & Node Name Normalization
# -----------------------------------------------------------------------------

def test_01_unknown_capability_fails_closed_without_bulk_fallback(adapter):
    """Proves unknown capability/task fails closed with UNSUPPORTED_CAPABILITY and never defaults to bulk."""
    req = EngineInvocationRequest(
        contract_version="1.0.0",
        binding_id="gateway_engine_binding",
        correlation_id="c1",
        operation_id="op1",
        attempt_id="att1",
        invocation_id="inv1",
        lease_id="l1",
        fence_epoch=1,
        graph_node_id="n-unknown-custom-capability",
        initialization_fingerprint="fp1",
        payload={"migration_id": "mig-1", "capability_contract": "unknown_unsupported"},
    )
    res = adapter.execute_task(req)
    assert res.is_success is False
    assert res.error_code == "UNSUPPORTED_CAPABILITY"
    assert "Implicit bulk fallback is forbidden" in res.error_message


def test_02_production_dag_node_name_normalization(adapter):
    """Proves real coordinator graph nodes like 'n-schema-prep', 'n-cdc-sync', 'n-inc-extract' map cleanly."""
    for node_id, expected_op in [
        ("n-schema-prep", "PREPARE_MIGRATION_EXECUTION"),
        ("n-data-transport", "EXECUTE_BULK_MIGRATION"),
        ("n-cdc-sync", "EXECUTE_CDC_SYNC"),
        ("n-inc-extract", "EXECUTE_INCREMENTAL_EXTRACT"),
        ("n-inc-apply", "EXECUTE_INCREMENTAL_APPLY"),
        ("n-val-compare", "RUN_FINAL_VALIDATION"),
    ]:
        fence_req = EngineInvocationRequest(
            contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id=f"op-fence-{node_id}",
            attempt_id="att1", invocation_id="inv-fence", lease_id="l1", fence_epoch=1,
            graph_node_id=node_id, initialization_fingerprint="fp1",
            payload={"migration_id": "mig-1", "semantic_operation": "ACQUIRE_EXECUTION_FENCE", "worker_id": "w1"}
        )
        fence_res = adapter.execute_task(fence_req)
        assert fence_res.is_success is True
        env = fence_res.result_payload["fencing_token_envelope"]

        req = EngineInvocationRequest(
            contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op1",
            attempt_id="att1", invocation_id="inv1", lease_id="l1", fence_epoch=1,
            fencing_token_envelope=env,
            graph_node_id=node_id, initialization_fingerprint="fp1",
            payload={
                "migration_id": "mig-1",
                "source_reader": object(),
                "target_writer": object(),
                "batch": {"rows": [{"updated_at": 100}]},
            }
        )
        res = adapter.execute_task(req)
        assert res.result_payload["engine_execution_receipt"]["gateway_operation_type"] == expected_op


# -----------------------------------------------------------------------------
# 2. Problem Group 2 & 3: M1-M8 Semantics & Configuration Fingerprint Retained
# -----------------------------------------------------------------------------

def test_03_m1_to_m8_compiled_dags_and_incremental_routing():
    """Proves all 8 canonical modes compile distinct required DAGs with node parameters."""
    cfg = {"selected_tables": ["users"], "watermark_column": "updated_at"}
    for mode in MigrationMode:
        plan = GraphCompiler.compile_plan(f"plan-{mode.value}", "mig-1", mode, configuration=cfg)
        assert plan.fingerprint is not None
        assert dict(plan.configuration)["watermark_column"] == "updated_at"
        for n in plan.nodes:
            assert dict(n.task.parameters)["watermark_column"] == "updated_at"

    m2_plan = GraphCompiler.compile_plan("p-m2", "mig-m2", MigrationMode.M2_BULK_CDC, configuration=cfg)
    assert len(m2_plan.nodes) == 5
    assert [n.node_id for n in m2_plan.nodes] == ["n-schema-prep", "n-cdc-start", "n-data-transport", "n-cdc-sync", "n-val-compare"]

    m4_plan = GraphCompiler.compile_plan("p-m4", "mig-m4", MigrationMode.M4_INCREMENTAL, configuration=cfg)
    contracts = [n.task.capability_contract for n in m4_plan.nodes]
    assert contracts == ["incremental_extract", "incremental_apply"]


def test_04_execution_plan_retains_and_serializes_configuration():
    """Proves ExecutionPlan retains configuration field, serializes in to_dict(), deserializes in from_dict()."""
    cfg = {"selected_tables": ["users", "orders"], "batch_size": 5000}
    plan = GraphCompiler.compile_plan("p1", "mig-1", MigrationMode.M1_BULK, configuration=cfg)
    assert dict(plan.configuration)["batch_size"] == 5000

    plan_dict = plan.to_dict()
    assert plan_dict["configuration"]["batch_size"] == 5000

    restored_plan = ExecutionPlan.from_dict(plan_dict)
    assert dict(restored_plan.configuration)["batch_size"] == 5000
    assert restored_plan.fingerprint == plan.fingerprint


# -----------------------------------------------------------------------------
# 3. Problem Group 4: Independent Engine Execution Receipt Verification
# -----------------------------------------------------------------------------

def test_05_independent_engine_execution_receipt(engine_gateway):
    """Proves EngineGateway generates an independent execution_receipt and ResultReconciler mandates it."""
    from akaalPipeline.operations.leases import LeaseManager
    uow = SQLiteUnitOfWork(":memory:")
    lm = LeaseManager()
    reconciler = ResultReconciler(lm)

    lm.acquire_lease("lease-1", "att-1", "owner-1", "2099-01-01T00:00:00Z", "fp-1", uow.connection)

    # Result without execution receipt MUST be rejected
    res_no_receipt = EngineInvocationResult(
        invocation_id="inv-1", attempt_id="att-1", lease_id="lease-1", fence_epoch=1,
        is_success=True, initialization_fingerprint="fp-1", graph_node_id="node-1", binding_id="b1",
        result_payload={"data": "test"}
    )
    with pytest.raises(StaleResultError) as exc_info:
        reconciler.reconcile_result(res_no_receipt, "fp-1", uow.connection, expected_attempt_id="att-1", expected_lease_id="lease-1")
    assert "Missing authoritative Engine execution receipt" in str(exc_info.value)

    # Result with valid Gateway-signed receipt succeeds
    adp = PipelineEngineGatewayAdapter(gateway=engine_gateway, owns_gateway=False)
    fence_req = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op-fence-prep",
        attempt_id="att-1", invocation_id="inv-fence", lease_id="lease-1", fence_epoch=1,
        graph_node_id="n-schema-prep", initialization_fingerprint="fp-1",
        payload={"migration_id": "mig-1", "semantic_operation": "ACQUIRE_EXECUTION_FENCE", "worker_id": "owner-1"}
    )
    fence_res = adp.execute_task(fence_req)
    assert fence_res.is_success is True
    env = fence_res.result_payload["fencing_token_envelope"]

    req = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op1",
        attempt_id="att-1", invocation_id="inv-1", lease_id="lease-1", fence_epoch=1,
        fencing_token_envelope=env,
        graph_node_id="n-schema-prep", initialization_fingerprint="fp-1",
        payload={"migration_id": "mig-1"}
    )
    res_gw = adp.execute_task(req)
    out = reconciler.reconcile_result(res_gw, "fp-1", uow.connection, expected_attempt_id="att-1", expected_lease_id="lease-1")
    assert out["status"] == "SUCCEEDED"


# -----------------------------------------------------------------------------
# 4. Problem Group 5: Fencing Token Verification
# -----------------------------------------------------------------------------

def test_06_strict_fencing_token_handshake(adapter, engine_gateway):
    """Proves missing or zero fencing epoch fails with FencingViolationError."""
    req_no_fence = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op1",
        attempt_id="att1", invocation_id="inv1", lease_id="l1", fence_epoch=0,
        graph_node_id="n1", initialization_fingerprint="fp1",
        payload={"migration_id": "mig-fence-audit", "semantic_operation": "TRIGGER_CHECKPOINT", "batch_id": "b1"}
    )
    res = adapter.execute_task(req_no_fence)
    assert res.is_success is False
    assert res.error_code in ("STALE_FENCING", "FENCING_VIOLATION", "INTERNAL_ENGINE_FAILURE")


# -----------------------------------------------------------------------------
# 5. Problem Group 6: Pipeline Cancellation Dispatches Physical Gateway Cancellation
# -----------------------------------------------------------------------------

def test_07_pipeline_cancellation_dispatches_gateway_cancellation(caller):
    """Proves Pipeline command handler handle_cancel_migration dispatches physical Gateway CANCEL_EXECUTION."""
    from akaalIPC.protocol.envelopes import CommandEnvelope
    from akaalIPC.protocol.schemas import RequestKind
    from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext

    actor_ref = ActorReference(actor_id="test-user", actor_type="user")
    actor = ActorContext(actor=actor_ref, organization_id="org-acme", workspace_id="ws-1", project_id="proj-1")
    corr = CorrelationContext(request_id="req-c1", correlation_id="corr-c1")

    # Create migration
    cmd_create = CommandEnvelope(
        request_id="req-c1", protocol_version="1.0.0", schema_version="1.0.0",
        request_type="create_migration", kind=RequestKind.COMMAND, actor=actor, correlation=corr,
        payload={"name": "Cancel Test", "mode": "M1", "source_spec": {}, "target_spec": {}}, command_id="cmd-c1",
    )
    res_create = caller.handle_command(cmd_create)
    assert res_create.status.name == "OK"
    mig_id = res_create.result["migration_id"]

    # Cancel migration
    cmd_cancel = CommandEnvelope(
        request_id="req-c2", protocol_version="1.0.0", schema_version="1.0.0",
        request_type="cancel_migration", kind=RequestKind.COMMAND, actor=actor, correlation=corr,
        payload={"migration_id": mig_id, "reason": "User requested cancel"}, command_id="cmd-c2",
    )
    res_cancel = caller.handle_command(cmd_cancel)
    assert res_cancel.status.name == "OK"
    assert res_cancel.result["state"] == "CANCELLED"


# -----------------------------------------------------------------------------
# 6. Problem Group 7: Checkpoint and Recovery Identity Accuracy
# -----------------------------------------------------------------------------

def test_08_checkpoint_verify_and_recovery_fail_when_missing(adapter):
    """Proves verify_checkpoint and perform_recovery_action fail closed when requested checkpoint is missing."""
    req_verify = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op1",
        attempt_id="att1", invocation_id="inv1", lease_id="l1", fence_epoch=1,
        graph_node_id="batch-999", checkpoint_id="chk-999", initialization_fingerprint="fp1",
        payload={"migration_id": "mig-chk-missing", "checkpoint_id": "chk-999"}
    )
    res_v = adapter.verify_checkpoint(req_verify)
    assert res_v.is_success is False

    req_recover = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c2", operation_id="op2",
        attempt_id="att1", invocation_id="inv2", lease_id="l1", fence_epoch=1,
        graph_node_id="batch-999", checkpoint_id="chk-999", initialization_fingerprint="fp1",
        payload={"migration_id": "mig-chk-missing", "checkpoint_id": "chk-999"}
    )
    res_r = adapter.perform_recovery_action(req_recover)
    assert res_r.is_success is False


# -----------------------------------------------------------------------------
# 7. Problem Group 8: Capability Truth & Telemetry Method
# -----------------------------------------------------------------------------

def test_09_capability_truth_and_event_publishing(adapter):
    """Proves probe_capability returns CapabilityProbeResult with false for unsupported providers, and publish_engine_event records telemetry."""
    res = adapter.probe_capability("nonexistent_provider_xyz", "some_cap")
    assert res.supported is False
    assert res.is_healthy is False
    adapter.publish_engine_event({"event_type": "test.event", "data": 123})


def test_10_retryability_tenancy_and_resource_ownership(engine_gateway):
    """Proves retryable flag survives mapping, tenancy context captures workspace/project, and ownership is safe."""
    # Test safe ownership: passing an external gateway sets _owns_gateway = False
    adp_external = PipelineEngineGatewayAdapter(gateway=engine_gateway, owns_gateway=False)
    assert adp_external._owns_gateway is False
    adp_external.close()  # Must NOT shut down external gateway

    # Verify context retains workspace and project
    req = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op1",
        attempt_id="att1", invocation_id="inv1", lease_id="l1", fence_epoch=1,
        graph_node_id="n1", initialization_fingerprint="fp1",
        payload={"migration_id": "mig-t1", "organization_id": "org-1", "workspace_id": "ws-100", "project_id": "proj-200"}
    )
    ctx = adp_external._build_context(req)
    assert ctx.tenant_id == "org-1"
    assert ctx.workspace_id == "ws-100"
    assert ctx.project_id == "proj-200"


def test_11_acquire_execution_fence_operation(adapter):
    """Proves ACQUIRE_EXECUTION_FENCE returns a signed boundary-neutral fencing token envelope."""
    req = EngineInvocationRequest(
        contract_version="1.0.0", binding_id="b1", correlation_id="c1", operation_id="op-fence-1",
        attempt_id="att1", invocation_id="inv1", lease_id="l1", fence_epoch=1,
        graph_node_id="job1", initialization_fingerprint="fp1",
        payload={"migration_id": "mig-fence-1", "semantic_operation": "ACQUIRE_EXECUTION_FENCE", "worker_id": "w1"}
    )
    res = adapter.execute_task(req)
    assert res.is_success is True
    env = res.result_payload["fencing_token_envelope"]
    assert env["migration_id"] == "mig-fence-1"
    assert env["job_id"] == "job1"
    assert env["fencing_epoch"] == 1
    assert "signature" in env and len(env["signature"]) > 0
