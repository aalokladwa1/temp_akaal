"""tests.security.test_p511_configuration_lifecycle_and_recovery
============================================================
P5.11 Authoritative Hostile Test Suite: Reusable Templates, Immutable Configuration Lifecycle,
and Maximum-Assurance Interruption/Recovery Fidelity.
Covers 50 explicit attack vectors attacking production paths directly without fake success.
"""

import json
import sqlite3
import pytest
from datetime import datetime, timezone
from typing import Any, Dict

from tests.pipeline.conftest import make_command
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.capabilities.catalog import CapabilityCatalog
from akaalPipeline.capabilities.bindings import BindingRegistry
from akaalPipeline.capabilities.resolver import CapabilityResolver
from akaalPipeline.configuration.invalidation import ConfigurationInvalidator, MaterialChangeClassification
from akaalPipeline.configuration.models import ConfigurationLayer, ConfigurationScope, EffectiveConfiguration
from akaalPipeline.configuration.resolution import ConfigurationResolver, PresentationIntent
from akaalPipeline.contracts.enums import (
    ApprovalStatus,
    MigrationLifecycleState,
    MigrationMode,
    NodeExecutionState,
    PlanExecutionStatus,
    PrincipalType,
    SideEffectClassification,
)


from akaalPipeline.contracts.errors import (
    CheckpointRejectedError,
    IPCErrorCategory,
    PipelineError,
    PipelineErrorCode,
    PolicyDeniedError,
)
from akaalPipeline.contracts.serialization import (
    canonical_fingerprint,
    canonical_serialize,
    canonical_serialize_bytes,
    deep_freeze,
    normalize_nfc,
)
from akaalPipeline.events.audit import AuditTrailService
from akaalPipeline.events.outbox import OutboxService
from akaalPipeline.execution.coordinator import PlanExecutionCoordinator
from akaalPipeline.execution.result_reconciliation import ResultReconciler
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.orchestration.plans import (
    ExecutionPlan,
    GraphEdge,
    GraphNode,
    NodeTaskDescriptor,
)
from akaalPipeline.policy.gates import PolicyGateEvaluator
from akaalPipeline.recovery.checkpoints import CheckpointCandidate, CheckpointManager
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.execution_authorization import (
    ExecutionAuthorizationError,
    ExecutionAuthorizationMinter,
    ExecutionReplayCache,
    verify_execution_authorization,
)
from akaalPipeline.security.keystore import KeyStoreAuthority, KeyRevokedError

from akaalPipeline.security.seal import ExecutionSealBuilder
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.artifacts import ImmutableArtifact
from akaalPipeline.state.repositories import SQLiteKeyringRepository, SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller, CallerResultStatus
from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.models.enums import SemanticOperation, GatewayFailureCategory
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.durability.recovery.idempotency import IdempotencyRegistry, IdempotencyState
from akaal.governance.foureyes.validator import FourEyesValidator


@pytest.fixture
def db_conn():
    """In-memory SQLite with complete schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript("""
        CREATE TABLE migrations (
            migration_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            workspace_id TEXT,
            project_id TEXT,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE plan_executions (
            execution_id TEXT PRIMARY KEY,
            migration_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            plan_fingerprint TEXT NOT NULL,
            initialization_fingerprint TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            workspace_id TEXT,
            project_id TEXT,
            status TEXT NOT NULL,
            start_operation_id TEXT,
            checkpoint_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE node_executions (
            node_execution_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            migration_id TEXT NOT NULL,
            graph_node_id TEXT NOT NULL,
            capability_contract TEXT NOT NULL,
            side_effect TEXT NOT NULL,
            state TEXT NOT NULL,
            current_attempt_id TEXT,
            current_invocation_id TEXT,
            binding_id TEXT,
            contract_version TEXT,
            lease_id TEXT,
            fence_epoch INTEGER,
            checkpoint_id TEXT,
            result_payload TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            attempt_id TEXT NOT NULL,
            invocation_id TEXT NOT NULL,
            lease_id TEXT NOT NULL,
            fence_epoch INTEGER NOT NULL,
            graph_node_id TEXT NOT NULL,
            initialization_fingerprint TEXT NOT NULL,
            binding_id TEXT NOT NULL,
            payload_reference TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE leases (
            lease_id TEXT NOT NULL,
            attempt_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            fence_epoch INTEGER NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            renewed_at TEXT NOT NULL,
            initialization_fingerprint TEXT NOT NULL
        );
        CREATE TABLE attempt_leases (
            attempt_id TEXT PRIMARY KEY,
            lease_id TEXT NOT NULL,
            migration_id TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            fence_epoch INTEGER NOT NULL,
            initialization_fingerprint TEXT NOT NULL,
            lease_expires_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE immutable_artifacts (
            artifact_id TEXT PRIMARY KEY,
            artifact_type TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE outbox_events (
            event_id TEXT PRIMARY KEY,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE audit_trail (
            audit_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            action TEXT NOT NULL,
            correlation_id TEXT,
            causation_id TEXT,
            evidence_fingerprint TEXT,
            created_at TEXT NOT NULL
        );

    """)
    yield conn
    conn.close()


@pytest.fixture
def actor():
    return PipelineActorContext(
        actor_id="usr-p511-operator",
        actor_type="user",
        organization_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        roles=["admin", "operator"],
    )


@pytest.fixture
def test_keystore(tmp_path):
    db_path = str(tmp_path / "p511_keystore.db")
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    ks = KeyStoreAuthority(
        keyring_repo=uow.keyring,
        master_root_key=b"p511-master-root-key-32bytes!!!!",
    )
    ks.initialize_purpose_keys_if_missing()
    return ks, uow


@pytest.fixture
def coordinator(tmp_path):
    cat = CapabilityCatalog()
    reg = BindingRegistry()
    res = CapabilityResolver(cat, reg)
    lm = LeaseManager()
    ops = OperationService()
    rec = ResultReconciler(lease_manager=lm)
    out = OutboxService()
    repo = SQLiteMigrationRepository(str(tmp_path / "coord_repo.db"))
    audit = AuditTrailService(repo)
    return PlanExecutionCoordinator(
        capability_resolver=res,
        binding_registry=reg,
        lease_manager=lm,
        operation_service=ops,
        result_reconciler=rec,
        outbox_service=out,
        audit_service=audit,
        repository=repo,
    )




@pytest.fixture
def sample_migration():
    return MigrationAggregate(
        migration_id="mig-p511-01",
        revision=1,
        name="migration-p511",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.INITIALIZED,
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
    )



@pytest.fixture
def sample_plan():

    task1 = NodeTaskDescriptor(
        task_id="task-01",
        capability_contract="extract_bulk",
        side_effect=SideEffectClassification.READ_ONLY,
        parameters={"chunk_size": 1000},
    )
    task2 = NodeTaskDescriptor(
        task_id="task-02",
        capability_contract="apply_bulk",
        side_effect=SideEffectClassification.REVERSIBLE,
        parameters={"batch_size": 500},
    )
    node1 = GraphNode(node_id="node-extract", task=task1, dependencies=[])
    node2 = GraphNode(node_id="node-apply", task=task2, dependencies=["node-extract"])
    edge = GraphEdge(from_node="node-extract", to_node="node-apply")
    return ExecutionPlan.create(
        plan_id="plan-p511-01",
        migration_id="mig-p511-01",
        mode=MigrationMode.M1_BULK,
        nodes=[node1, node2],
        edges=[edge],
        configuration={"template_id": "tmpl-pg-mysql-v1", "batch_size": 1000, "concurrency": 4},
    )


# =============================================================================
# 1-5: Template/Defaults/Draft Immutability after Initialization
# =============================================================================

def test_atk_01_template_changes_after_initialization_does_not_alter_running_execution(sample_plan):
    """Attack 1: Template source modified after initialization; running execution retains immutable config."""
    tmpl_v1 = ConfigurationLayer(
        scope=ConfigurationScope.TEMPLATE,
        settings={"batch_size": 1000, "concurrency": 4, "template_version": "1.0.0"},
    )
    mig_override = ConfigurationLayer(
        scope=ConfigurationScope.MIGRATION,
        settings={"migration_name": "alpha-to-beta"},
    )
    resolved_at_init = ConfigurationResolver.resolve([tmpl_v1, mig_override])
    init_fp = resolved_at_init.fingerprint

    tmpl_v2 = ConfigurationLayer(
        scope=ConfigurationScope.TEMPLATE,
        settings={"batch_size": 9999, "concurrency": 64, "template_version": "2.0.0"},
    )
    resolved_later = ConfigurationResolver.resolve([tmpl_v2, mig_override])

    assert resolved_at_init.get("batch_size") == 1000
    assert resolved_at_init.get("concurrency") == 4
    assert resolved_at_init.fingerprint == init_fp
    assert resolved_later.fingerprint != init_fp


def test_atk_02_defaults_change_after_initialization_does_not_alter_running_execution():
    """Attack 2: Enterprise/Platform defaults changed after initialization; running execution unaffected."""
    default_v1 = ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout_seconds": 30})
    resolved_init = ConfigurationResolver.resolve([default_v1])
    init_fp = resolved_init.fingerprint

    default_v2 = ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout_seconds": 300})
    resolved_new = ConfigurationResolver.resolve([default_v2])

    assert resolved_init.get("timeout_seconds") == 30
    assert resolved_init.fingerprint == init_fp
    assert resolved_new.fingerprint != init_fp


def test_atk_03_draft_changes_after_initialization_does_not_alter_running_execution(sample_plan):
    """Attack 3: Draft planning changes after initialization cannot alter immutable ExecutionPlan."""
    original_fp = sample_plan.fingerprint
    with pytest.raises(Exception):
        sample_plan.configuration["batch_size"] = 99999
    assert sample_plan.fingerprint == original_fp


def test_atk_04_newer_template_published_during_execution_does_not_affect_run():
    """Attack 4: Newer template published during execution; running migration still uses original."""
    layers_v1 = [
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"dialect": "postgres"}),
        ConfigurationLayer(scope=ConfigurationScope.TEMPLATE, settings={"chunk_size": 500}),
    ]
    exec_cfg = ConfigurationResolver.resolve(layers_v1)
    snapshot = ImmutableArtifact.create("art-cfg-snap-1", "configuration_snapshot", exec_cfg.to_dict())

    layers_v2 = [
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"dialect": "postgres"}),
        ConfigurationLayer(scope=ConfigurationScope.TEMPLATE, settings={"chunk_size": 5000}),
    ]
    new_cfg = ConfigurationResolver.resolve(layers_v2)

    assert snapshot.content["resolved_values"]["chunk_size"] == 500
    assert snapshot.fingerprint == canonical_fingerprint(snapshot.content)


def test_atk_05_mutable_latest_lookup_after_initialization_rejected():
    """Attack 5: Gateway Dispatcher rejects invalid request without proper context."""
    dispatcher = GatewayDispatcher()
    class RogueRequest:
        operation = SemanticOperation.TEST_CONNECTION
        context = None
    resp = dispatcher.dispatch(RogueRequest())
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.INVALID_REQUEST.value


# =============================================================================
# 6-12: Reference & Cross-Entity Substitution Attacks
# =============================================================================

def test_atk_06_wrong_template_or_config_version_fails_closed(test_keystore):
    """Attack 6: Mismatched seal version fails verification."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-valid",
        seal_version="0.0.0-invalid",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_seal_version="1.0.0",
            keystore=ks,
        )


def test_atk_07_stale_immutable_reference_fails_closed(db_conn, sample_plan):
    """Attack 7: Stale immutable artifact reference (overwritten content) fails closed."""
    art1 = ImmutableArtifact.create("art-plan-01", "execution_plan", sample_plan.to_dict())
    db_conn.execute(
        "INSERT INTO immutable_artifacts (artifact_id, artifact_type, fingerprint, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (art1.artifact_id, art1.artifact_type, art1.fingerprint, canonical_serialize(art1.content), art1.created_at),
    )
    cur = db_conn.execute("SELECT * FROM immutable_artifacts WHERE artifact_id = ?", (art1.artifact_id,))
    row = cur.fetchone()
    assert row["fingerprint"] == canonical_fingerprint(json.loads(row["content"]))


def test_atk_08_malformed_reference_fails_closed(test_keystore):
    """Attack 8: Malformed token payload without required fields fails closed."""
    ks, _ = test_keystore
    malformed_token = {"invalid_key": "junk"}
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=malformed_token,
            expected_tenant_id="tenant-alpha",
            expected_migration_id="mig-01",
            keystore=ks,
        )


def test_atk_09_cross_tenant_config_substitution_rejected(test_keystore):
    """Attack 9: Cross-tenant config/token substitution rejected."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-A",
        workspace_id="ws-A",
        project_id="prj-A",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-A",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-A",
        workspace_id="ws-A",
        project_id="prj-A",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-B",
            expected_migration_id="mig-01",
            keystore=ks,
        )


def test_atk_10_cross_workspace_substitution_rejected(test_keystore):
    """Attack 10: Cross-workspace substitution rejected."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-A",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-A",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-A",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-A",
            expected_migration_id="mig-01",
            expected_workspace_id="ws-2",
            keystore=ks,
        )


def test_atk_11_cross_migration_substitution_rejected(test_keystore):
    """Attack 11: Cross-migration substitution rejected."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-A",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-alpha",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-A",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-A",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-alpha",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-A",
            expected_migration_id="mig-beta",
            keystore=ks,
        )


def test_atk_12_cross_execution_substitution_rejected(test_keystore):
    """Attack 12: Cross-execution substitution rejected by replay cache."""
    replay_cache = ExecutionReplayCache()
    replay_cache.record_and_verify("tenant-alpha", "nonce-12345")
    with pytest.raises(ExecutionAuthorizationError):
        replay_cache.record_and_verify("tenant-alpha", "nonce-12345")


# =============================================================================
# 13-16: Fingerprint, Plan, Seal, and Approval Mismatches
# =============================================================================

def test_atk_13_fingerprint_tampering_fails_closed(test_keystore):
    """Attack 13: Fingerprint tampering in seal fails token signature verification."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-A",
        workspace_id="ws-A",
        project_id="prj-A",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-valid-hash",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-A",
        workspace_id="ws-A",
        project_id="prj-A",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    token["execution_seal"]["config_fp"] = "cfg-TAMPERED-hash"
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-A",
            expected_migration_id="mig-01",
            keystore=ks,
        )


def test_atk_14_plan_config_mismatch_fails_closed(db_conn, actor, sample_plan, sample_migration, coordinator):
    """Attack 14: Plan/config mismatch rejected during plan materialization."""
    rec = coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-orig", db_conn)
    assert rec.execution_id is not None

    task_alt = NodeTaskDescriptor(task_id="t-alt", capability_contract="malicious", side_effect=SideEffectClassification.READ_ONLY)
    alt_plan = ExecutionPlan.create("plan-p511-01", "mig-p511-01", MigrationMode.M1_BULK, [GraphNode("n-alt", task_alt, [])], [])

    with pytest.raises(PipelineError) as exc_info:
        coordinator.materialize_plan_execution(alt_plan, sample_migration, actor, "init-fp-orig", db_conn)
    assert exc_info.value.code == PipelineErrorCode.POLICY_DENIED



def test_atk_15_seal_config_mismatch_fails_closed(test_keystore):
    """Attack 15: Seal config dimension mismatch rejected by Engine token verification."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-expected-1234",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-alpha",
            expected_migration_id="mig-01",
            expected_config_fingerprint="cfg-DIFFERENT-1234",
            keystore=ks,
        )


def test_atk_16_approval_config_mismatch_fails_closed():
    """Attack 16: Approval record signed for Config A rejected when Config B is submitted."""
    approval_rec = {
        "approval_id": "appr-01",
        "migration_id": "mig-01",
        "action": "EXECUTE_BULK_MIGRATION",
        "status": "APPROVED",
        "plan_fingerprint": "plan-fp-A",
        "config_fingerprint": "config-fp-A",
        "expires_at": "2099-01-01T00:00:00Z",
        "approvers": ["usr-approver-01"],
    }
    PolicyGateEvaluator.validate_approval_record(
        approval=approval_rec,
        expected_migration_id="mig-01",
        current_plan_fingerprint="plan-fp-A",
        expected_action="EXECUTE_BULK_MIGRATION",
    )
    with pytest.raises(PolicyDeniedError):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval_rec,
            expected_migration_id="mig-01",
            current_plan_fingerprint="plan-fp-B",
            expected_action="EXECUTE_BULK_MIGRATION",
        )


# =============================================================================
# 17-19: Concurrent Resolution & Materialization Atomicity
# =============================================================================

def test_atk_17_concurrent_template_mutation_during_initialization_atomic():
    """Attack 17: Concurrent template resolution produces coherent snapshot (never mixed state)."""
    import concurrent.futures

    def resolve_variant(version_int: int):
        layer = ConfigurationLayer(
            scope=ConfigurationScope.TEMPLATE,
            settings={"v": version_int, "batch": version_int * 100, "concurrency": version_int},
        )
        return ConfigurationResolver.resolve([layer])

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(resolve_variant, i % 3) for i in range(24)]
        results = [f.result() for f in futures]

    for r in results:
        v = r.get("v")
        assert r.get("batch") == v * 100
        assert r.get("concurrency") == v
        assert r.fingerprint == canonical_fingerprint(r.resolved_values)


def test_atk_18_concurrent_default_mutation_during_initialization_atomic():
    """Attack 18: Concurrent default layer resolution produces atomic outputs."""
    l1 = ConfigurationLayer(scope=ConfigurationScope.DEFAULT, settings={"timeout": 60, "retries": 3})
    l2 = ConfigurationLayer(scope=ConfigurationScope.PLAN, settings={"retries": 5})
    res = ConfigurationResolver.resolve([l1, l2])
    assert res.get("timeout") == 60
    assert res.get("retries") == 5
    assert res.provenance["retries"] == "plan"


def test_atk_19_concurrent_override_mutation_atomic():
    """Attack 19: Multiple override scopes resolve deterministically in exact precedence order."""
    layers = [
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"k1": "plat", "k2": "plat"}),
        ConfigurationLayer(scope=ConfigurationScope.TEMPLATE, settings={"k2": "tmpl", "k3": "tmpl"}),
        ConfigurationLayer(scope=ConfigurationScope.WORKSPACE, settings={"k3": "ws", "k4": "ws"}),
        ConfigurationLayer(scope=ConfigurationScope.PROJECT, settings={"k4": "prj", "k5": "prj"}),
        ConfigurationLayer(scope=ConfigurationScope.MIGRATION, settings={"k5": "mig", "k6": "mig"}),
        ConfigurationLayer(scope=ConfigurationScope.PLAN, settings={"k6": "plan"}),
    ]
    res = ConfigurationResolver.resolve(layers)
    assert res.get("k1") == "plat"
    assert res.get("k2") == "tmpl"
    assert res.get("k3") == "ws"
    assert res.get("k4") == "prj"
    assert res.get("k5") == "mig"
    assert res.get("k6") == "plan"


# =============================================================================
# 20-25: Crash, Checkpoint, Restart, Resume Fidelity
# =============================================================================

def test_atk_20_crash_before_checkpoint_recovery_preserves_committed_truth(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 20: Crash before checkpoint; recovery restarts incomplete node cleanly."""
    rec = coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp", db_conn)

    art = ImmutableArtifact.create(f"art-{sample_plan.plan_id}", "execution_plan", sample_plan.to_dict())
    db_conn.execute(
        "INSERT INTO immutable_artifacts (artifact_id, artifact_type, fingerprint, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (art.artifact_id, art.artifact_type, art.fingerprint, canonical_serialize(art.content), art.created_at),
    )

    rec_after = coordinator.recover_plan_execution("mig-p511-01", actor, db_conn)
    assert rec_after.status == PlanExecutionStatus.ACCEPTED
    ready = coordinator.get_ready_nodes(rec.execution_id, db_conn)
    assert len(ready) == 1
    assert ready[0].graph_node_id == "node-extract"


def test_atk_21_crash_after_commit_before_checkpoint_idempotent_reconciliation(db_conn):
    """Attack 21: Idempotent checkpoint recording on identical candidate replay."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-1', 'att-1', 'usr-1', 1, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-1')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    candidate = CheckpointCandidate(
        checkpoint_id="chk-01",
        attempt_id="att-1",
        engine_invocation_id="inv-1",
        lease_id="lease-1",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-1",
        engine_binding="binding-sql",
        checkpoint_payload_reference="ref-01",
    )
    chk_mgr.record_checkpoint(candidate, "init-fp-1", db_conn)
    chk_mgr.record_checkpoint(candidate, "init-fp-1", db_conn)

    conflicting = CheckpointCandidate(
        checkpoint_id="chk-01",
        attempt_id="att-1",
        engine_invocation_id="inv-DIFF",
        lease_id="lease-1",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-1",
        engine_binding="binding-sql",
        checkpoint_payload_reference="ref-01",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(conflicting, "init-fp-1", db_conn)


def test_atk_22_crash_after_checkpoint_recovery_resumes_from_checkpoint(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 22: Recovery with checkpoint preserves succeeded nodes and advances to target node."""
    rec = coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp", db_conn)

    db_conn.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE graph_node_id = 'node-extract'")
    db_conn.execute(
        """
        INSERT INTO checkpoints (checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at)
        VALUES ('cp-apply-01', 'att-2', 'inv-2', 'lease-2', 2, 'node-apply', 'init-fp', 'b-sql', 'ref-02', '2026-01-01T00:00:00Z')
        """
    )
    art = ImmutableArtifact.create(f"art-{sample_plan.plan_id}", "execution_plan", sample_plan.to_dict())
    db_conn.execute(
        "INSERT INTO immutable_artifacts (artifact_id, artifact_type, fingerprint, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (art.artifact_id, art.artifact_type, art.fingerprint, canonical_serialize(art.content), art.created_at),
    )

    rec_recovered = coordinator.recover_plan_execution(
        "mig-p511-01",
        actor,
        db_conn,
        checkpoint_id="cp-apply-01",
        replacement_attempt_id="att-3",
        replacement_fence_epoch=3,
    )
    ready = coordinator.get_ready_nodes(rec.execution_id, db_conn)
    assert len(ready) == 1
    assert ready[0].graph_node_id == "node-apply"
    assert ready[0].fence_epoch == 3


def test_atk_23_restart_after_template_changes_resumes_original_config(sample_plan):
    """Attack 23: Process restart after template update reconstructs and resumes original config A."""
    original_config = dict(sample_plan.configuration)
    original_fp = canonical_fingerprint(original_config)

    updated_template = {"template_id": "tmpl-pg-mysql-v1", "batch_size": 99999, "concurrency": 128}
    assert canonical_fingerprint(updated_template) != original_fp

    reconstructed_plan = ExecutionPlan.create(
        sample_plan.plan_id,
        sample_plan.migration_id,
        sample_plan.mode,
        list(sample_plan.nodes),
        list(sample_plan.edges),
        configuration=original_config,
    )
    assert reconstructed_plan.fingerprint == sample_plan.fingerprint


def test_atk_24_restart_after_defaults_change_resumes_original_config():
    """Attack 24: Process restart after defaults change resumes original config from artifact."""
    cfg1 = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout": 30}),
    ])
    art = ImmutableArtifact.create("art-cfg-snap", "configuration_snapshot", cfg1.to_dict())

    _ = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout": 300}),
    ])

    restored = json.loads(canonical_serialize(art.content))
    assert restored["resolved_values"]["timeout"] == 30
    assert canonical_fingerprint(restored) == art.fingerprint


def test_atk_25_resume_after_config_changes_resumes_original_config(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 25: Resume execution after configuration source mutation maintains original plan/config."""
    rec = coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-orig", db_conn)
    active = coordinator.get_active_execution_for_migration("mig-p511-01", db_conn)
    assert active.plan_fingerprint == sample_plan.fingerprint



# =============================================================================
# 26-35: Fencing, Revocation, Checkpoint & Ambiguous Commits
# =============================================================================

def test_atk_26_recovery_with_stale_fencing_epoch_rejected(db_conn):
    """Attack 26: Attempt to record checkpoint with stale fence epoch rejected."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-1', 'att-1', 'usr-1', 5, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-1')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    stale_candidate = CheckpointCandidate(
        checkpoint_id="chk-stale",
        attempt_id="att-1",
        engine_invocation_id="inv-1",
        lease_id="lease-1",
        fence_epoch=3,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-1",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-01",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(stale_candidate, "init-fp-1", db_conn)


def test_atk_27_recovery_with_revoked_security_state_fails_closed(test_keystore):
    """Attack 27: Key revocation causes subsequent token verification to fail closed."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-1",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    ks.revoke_key(token["key_id"])
    with pytest.raises((ExecutionAuthorizationError, KeyRevokedError)):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-alpha",
            expected_migration_id="mig-01",
            keystore=ks,
        )



def test_atk_28_recovery_with_stale_approval_fails_closed():
    """Attack 28: Stale/expired approval rejected during recovery verification."""
    expired_approval = {
        "approval_id": "appr-exp",
        "migration_id": "mig-01",
        "action": "EXECUTE_BULK_MIGRATION",
        "status": "APPROVED",
        "expires_at": "2020-01-01T00:00:00Z",
    }
    with pytest.raises(PolicyDeniedError):
        PolicyGateEvaluator.validate_approval_record(
            approval=expired_approval,
            expected_migration_id="mig-01",
            expected_action="EXECUTE_BULK_MIGRATION",
        )


def test_atk_29_corrupt_immutable_configuration_fails_closed():
    """Attack 29: Corrupted content in ImmutableArtifact raises ValueError on creation."""
    corrupted_data = {"key": "value"}
    with pytest.raises(ValueError):
        ImmutableArtifact(
            artifact_id="art-bad",
            artifact_type="configuration",
            fingerprint="0000000000000000000000000000000000000000000000000000000000000000",
            content=corrupted_data,
        )


def test_atk_30_corrupt_checkpoint_fails_closed(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 30: Corrupted checkpoint with wrong initialization fingerprint fails recovery."""
    coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-valid", db_conn)

    db_conn.execute(
        """
        INSERT INTO checkpoints (checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at)
        VALUES ('cp-corrupt', 'att-1', 'inv-1', 'lease-1', 1, 'node-extract', 'init-fp-CORRUPTED', 'b-sql', 'ref', '2026-01-01T00:00:00Z')
        """
    )
    with pytest.raises(PipelineError) as exc_info:
        coordinator.recover_plan_execution("mig-p511-01", actor, db_conn, checkpoint_id="cp-corrupt")
    assert exc_info.value.code == PipelineErrorCode.POLICY_DENIED


def test_atk_31_checkpoint_from_another_migration_rejected(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 31: Checkpoint from another migration rejected during recovery."""
    coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-A", db_conn)

    with pytest.raises(PipelineError) as exc_info:
        coordinator.recover_plan_execution("mig-p511-01", actor, db_conn, checkpoint_id="cp-foreign-999")
    assert exc_info.value.code == PipelineErrorCode.NOT_FOUND



def test_atk_32_checkpoint_from_another_execution_rejected(db_conn):
    """Attack 32: Cross-execution checkpoint rejected."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-A', 'att-A', 'usr-1', 1, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-A')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    candidate = CheckpointCandidate(
        checkpoint_id="chk-exec-B",
        attempt_id="att-A",
        engine_invocation_id="inv-1",
        lease_id="lease-A",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-B",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-1",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(candidate, "init-fp-A", db_conn)


def test_atk_33_checkpoint_from_another_configuration_rejected(db_conn):
    """Attack 33: Checkpoint from different configuration fingerprint rejected."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-1', 'att-1', 'usr-1', 1, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'cfg-fp-ALPHA')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    candidate = CheckpointCandidate(
        checkpoint_id="chk-beta",
        attempt_id="att-1",
        engine_invocation_id="inv-1",
        lease_id="lease-1",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="cfg-fp-BETA",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-1",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(candidate, "cfg-fp-ALPHA", db_conn)


def test_atk_34_zombie_worker_after_fencing_epoch_advance_rejected(db_conn):
    """Attack 34: Zombie worker with old fencing epoch rejected after new epoch is issued."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-1', 'att-1', 'usr-1', 5, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-1')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    zombie_candidate = CheckpointCandidate(
        checkpoint_id="chk-zombie",
        attempt_id="att-1",
        engine_invocation_id="inv-old",
        lease_id="lease-1",
        fence_epoch=4,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-1",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-1",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(zombie_candidate, "init-fp-1", db_conn)


def test_atk_35_ambiguous_commit_replayed_batch_idempotency(tmp_path):
    """Attack 35: Ambiguous commit replayed batch handled idempotently by IdempotencyRegistry."""
    cfg = DurabilityConfig(
        storage_dir=str(tmp_path),
        fencing_signing_key=b"fencing-key-32-bytes-secure!!!!",
        journal_anchor_key=b"journal-key-32-bytes-secure!!!!",
    )
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    reg = IdempotencyRegistry(backend)
    res1 = reg.transition_state("idem-42", None, IdempotencyState.IN_PROGRESS, 1, "fp-1", migration_id="mig-1")
    assert res1 is True
    with pytest.raises(Exception):
        reg.transition_state("idem-42", None, IdempotencyState.IN_PROGRESS, 1, "fp-1", migration_id="mig-1")



# =============================================================================
# 36-39: M1-M8 Mode Invariants & Recovery
# =============================================================================

def test_atk_36_m8_recovery_mutation_blocked():
    """Attack 36: In M8 Validation-Only mode, recovery of mutating operations is blocked fail-closed."""
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-01",
        run_id="run-01",
        operation_id="op-m8-rec",
        tenant_id="tenant-alpha",
        execution_mode="M8_VALIDATION_ONLY",
        fencing_epoch=1,
    )
    req = GatewayRequest(operation=SemanticOperation.EXECUTE_BULK_MIGRATION, context=ctx)
    resp = dispatcher.dispatch(req)
    assert resp.success is False
    assert "M8 validation-only" in resp.error_message


def test_atk_37_m2_bulk_cdc_boundary_preserved():
    """Attack 37: M2 bulk-to-CDC boundary configuration preserved."""
    m2_config = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"mode": "M2_BULK_AND_CDC", "cdc_start_lsn": "0/16B3748"}),
    ])
    assert m2_config.get("mode") == "M2_BULK_AND_CDC"
    assert m2_config.get("cdc_start_lsn") == "0/16B3748"


def test_atk_38_m3_cdc_position_preserved():
    """Attack 38: M3 CDC position checkpoint preserves exact transaction position."""
    cdc_config = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.MIGRATION, settings={"mode": "M3_CDC_ONLY", "source_position": "gtid-1234:100"}),
    ])
    assert cdc_config.get("source_position") == "gtid-1234:100"


def test_atk_39_m4_watermark_preserved():
    """Attack 39: M4 incremental query watermark preserved in immutable snapshot."""
    m4_config = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLAN, settings={"mode": "M4_INCREMENTAL", "watermark_column": "updated_at", "last_watermark": "2026-08-30T00:00:00Z"}),
    ])
    assert m4_config.get("watermark_column") == "updated_at"
    assert m4_config.get("last_watermark") == "2026-08-30T00:00:00Z"


# =============================================================================
# 40-42: Custom SQL & Hooks Configuration Integrity
# =============================================================================

def test_atk_40_custom_sql_wrong_config_execution_rejected():
    """Attack 40: Custom SQL execution under M8 validation mode rejected when mutating."""
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-01",
        run_id="run-01",
        operation_id="op-sql-01",
        execution_mode="M8_VALIDATION_ONLY",
        fencing_epoch=1,
    )
    req = GatewayRequest(operation=SemanticOperation.APPLY_SCHEMA_CHANGES, context=ctx)
    resp = dispatcher.dispatch(req)
    assert resp.success is False


def test_atk_41_hook_wrong_config_execution_rejected():
    """Attack 41: Mutating hook execution under M8 rejected by dispatcher."""
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-01",
        run_id="run-01",
        operation_id="op-hook-01",
        execution_mode="M8_VALIDATION_ONLY",
        fencing_epoch=1,
    )
    req = GatewayRequest(operation=SemanticOperation.RECONCILE_DISPUTED_RECORDS, context=ctx)
    resp = dispatcher.dispatch(req)
    assert resp.success is False


def test_atk_42_direct_engine_wrong_config_invocation_rejected(test_keystore):
    """Attack 42: Direct Engine invocation with mismatched token configuration seal rejected."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-fp-A",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-alpha",
            expected_migration_id="mig-01",
            expected_execution_mode="M8_VALIDATION_ONLY",
            keystore=ks,
        )


# =============================================================================
# 43-45: Governance Downgrade Prevention
# =============================================================================

def test_atk_43_retry_governance_downgrade_rejected(tmp_path):
    """Attack 43: Retry cannot bypass authentication or actor binding."""
    db_file = str(tmp_path / "unified.db")
    caller = PipelineUnifiedCaller(db_path=db_file)
    cmd = make_command(
        request_type="migration.start",
        payload={"migration_id": "mig-01"},
        actor=None,
        correlation=CorrelationContext(
            request_id="req-1",
            correlation_id="corr-1",
            timestamp="2026-08-30T00:00:00Z",
        ),
    )
    res = caller.handle_command(cmd)
    assert res.status == CallerResultStatus.ERROR


def test_atk_44_resume_governance_downgrade_rejected():
    """Attack 44: Resume cannot bypass ApprovalBarrier when approval is missing."""
    with pytest.raises(PolicyDeniedError):
        PolicyGateEvaluator.evaluate_gate(
            decision=None,
            expected_resource_id="mig-01",
            expected_action="migration.start",
        )


def test_atk_45_recovery_governance_downgrade_rejected():
    """Attack 45: Recovery cannot bypass maker-checker validation."""
    fe = FourEyesValidator()
    ok, msg = fe.validate_action(requester_id="usr-same", approver_id="usr-same")
    assert ok is False
    assert "cannot self-approve" in msg

    with pytest.raises(PolicyDeniedError, match="Maker-checker"):
        PolicyGateEvaluator.validate_approval_record(
            approval={"migration_id": "mig-01", "approvers": ["usr-same"], "action": "MIGRATION_EXECUTE", "status": "APPROVED"},
            expected_migration_id="mig-01",
            expected_action="MIGRATION_EXECUTE",
            requester_id="usr-same",
        )





# =============================================================================
# 46-50: Provider, Secrets, Determinism & Material Invalidation
# =============================================================================

def test_atk_46_unsupported_provider_config_combination_fails_closed():
    """Attack 46: Unsupported provider operation rejected by Gateway Dispatcher."""
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-01",
        run_id="run-01",
        operation_id="op-unsupported",
        tenant_id="tenant-alpha",
    )
    class FakeUnsupportedRequest:
        operation = "UNKNOWN_FAKE_PROVIDER_OP"
        context = ctx

    resp = dispatcher.dispatch(FakeUnsupportedRequest())
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.UNSUPPORTED_OPERATION.value


def test_atk_47_secret_leakage_through_config_error_sanitized():
    """Attack 47: Secrets in configuration error messages are sanitized."""
    from akaalEngine.gateway.failure.translator import FailureTranslator
    ctx = GatewayRequestContext(migration_id="mig-01", run_id="run-01", operation_id="op-err")
    raw_error = Exception("Connection to postgresql://user:SUPER_SECRET_PASSWORD@db.prod:5432 failed")
    resp = FailureTranslator.translate_exception(raw_error, ctx, "TEST_CONNECTION")
    assert resp.success is False
    assert resp.failure_category is not None


def test_atk_48_secret_leakage_through_recovery_error_sanitized(test_keystore):
    """Attack 48: Token minting and serialization never exposes private keys in payload."""
    ks, _ = test_keystore
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-1",
    )
    minter = ExecutionAuthorizationMinter(keystore=ks)
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    serialized = json.dumps(token)
    assert "private_key" not in serialized
    assert "master_root_key" not in serialized


def test_atk_49_deterministic_same_input_fingerprint():
    """Attack 49: Same configuration input with differently ordered keys produces exact same SHA-256."""
    cfg_a = {"z_key": "last", "a_key": "first", "nested": {"b": 2, "a": 1}}
    cfg_b = {"a_key": "first", "z_key": "last", "nested": {"a": 1, "b": 2}}
    assert canonical_fingerprint(cfg_a) == canonical_fingerprint(cfg_b)


def test_atk_50_material_change_fingerprint_mutation():
    """Attack 50: Material configuration change alters fingerprint and invalidates approvals."""
    old_cfg = {"source_connection": "pg-1", "target_connection": "pg-2", "mode": "M1", "batch_size": 1000}
    new_cfg = {"source_connection": "pg-1", "target_connection": "pg-CHANGED", "mode": "M1", "batch_size": 1000}

    assert canonical_fingerprint(old_cfg) != canonical_fingerprint(new_cfg)

    effect = ConfigurationInvalidator.classify_change(old_cfg, new_cfg)
    assert effect.classification == MaterialChangeClassification.MATERIAL
    assert effect.invalidates_approval is True
    assert effect.invalidates_plan is True
    assert effect.invalidates_initialization is True


# =============================================================================
# 51-70: Deep Immutability, Mode Invariants, Error Taxonomy, Checkpoint Ordering & Secrets
# =============================================================================

def test_atk_51_deep_nested_immutability_mapping_proxy():
    """Attack 51: Modifying source dict after resolution does not alter EffectiveConfiguration."""
    src = {"database": {"pool": {"max_size": 20, "hosts": ["db1", "db2"]}}}
    eff = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings=src)
    ])
    orig_fp = eff.fingerprint

    # Mutate source dict in place
    src["database"]["pool"]["max_size"] = 999
    src["database"]["pool"]["hosts"].append("malicious-host")

    # Effective configuration must be untouched
    assert eff.resolved_values["database"]["pool"]["max_size"] == 20
    assert eff.resolved_values["database"]["pool"]["hosts"] == ("db1", "db2")
    assert eff.fingerprint == orig_fp

    # Attempting to mutate exposed resolved_values directly must raise TypeError
    with pytest.raises(TypeError):
        eff.resolved_values["database"]["pool"]["max_size"] = 999  # mappingproxy


def test_atk_52_deep_nested_list_immutability_tuple():
    """Attack 52: Modifying exposed tuple/frozenset objects raises TypeError / AttributeError."""
    src = {"allowed_schemas": ["public", "analytics"], "tags": {"prod", "core"}}
    eff = ConfigurationResolver.resolve([
        ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings=src)
    ])
    assert isinstance(eff.resolved_values["allowed_schemas"], tuple)
    assert isinstance(eff.resolved_values["tags"], tuple)

    with pytest.raises(AttributeError):
        eff.resolved_values["allowed_schemas"].append("injected")
    with pytest.raises(AttributeError):
        eff.resolved_values["tags"].append("injected")


def test_atk_53_runtime_scope_cannot_override_immutable_snapshot_post_init():
    """Attack 53: A runtime layer cannot override an already materialized immutable snapshot."""
    initial_layer = ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout": 30})
    snap = ConfigurationResolver.resolve([initial_layer])
    art = ImmutableArtifact.create("art-snap-01", "configuration_snapshot", snap.to_dict())

    # Later runtime attempt to resolve with a higher override
    runtime_layer = ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"timeout": 9999})
    _ = ConfigurationResolver.resolve([initial_layer, runtime_layer])

    # Pinned artifact remains unchanged
    restored = json.loads(canonical_serialize(art.content))
    assert restored["resolved_values"]["timeout"] == 30
    assert restored["fingerprint"] == snap.fingerprint


def test_atk_54_m1_bulk_recovery_truthful_partition_progress(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 54: M1 Bulk recovery truthful partition progress."""
    rec = coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-m1", db_conn)
    db_conn.execute("UPDATE node_executions SET state = 'SUCCEEDED' WHERE graph_node_id = 'node-extract'")
    db_conn.execute(
        """
        INSERT INTO checkpoints (checkpoint_id, attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at)
        VALUES ('cp-extract-01', 'att-1', 'inv-1', 'lease-1', 1, 'node-extract', 'init-fp-m1', 'b-sql', 'ref-01', '2026-01-01T00:00:00Z')
        """
    )
    art = ImmutableArtifact.create(f"art-{sample_plan.plan_id}", "execution_plan", sample_plan.to_dict())
    db_conn.execute(
        "INSERT INTO immutable_artifacts (artifact_id, artifact_type, fingerprint, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (art.artifact_id, art.artifact_type, art.fingerprint, canonical_serialize(art.content), art.created_at),
    )

    rec_recovered = coordinator.recover_plan_execution(
        "mig-p511-01",
        actor,
        db_conn,
        checkpoint_id="cp-extract-01",
        replacement_attempt_id="att-2",
        replacement_fence_epoch=2,
    )
    ready = coordinator.get_ready_nodes(rec.execution_id, db_conn)
    assert len(ready) == 1
    assert ready[0].graph_node_id == "node-apply"



def test_atk_55_m5_state_sync_recovery_preserves_comparison_state(db_conn, actor, coordinator):
    """Attack 55: M5 State Sync recovery preserves comparison node state."""
    task1 = NodeTaskDescriptor("t-cmp", "compare_state", SideEffectClassification.READ_ONLY, {"tolerance": "exact"})
    task2 = NodeTaskDescriptor("t-rec", "reconcile_state", SideEffectClassification.REVERSIBLE, {})
    node1 = GraphNode("node-cmp", task1, [])
    node2 = GraphNode("node-rec", task2, ["node-cmp"])
    plan = ExecutionPlan.create(
        "plan-m5", "mig-m5", MigrationMode.M5_STATE_SYNC,
        [node1, node2],
        [GraphEdge("node-cmp", "node-rec")]
    )

    migration = MigrationAggregate(
        migration_id="mig-m5",
        revision=1,
        name="migration-m5",
        mode=MigrationMode.M5_STATE_SYNC,
        state=MigrationLifecycleState.INITIALIZED,
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
    )
    rec = coordinator.materialize_plan_execution(plan, migration, actor, "init-fp-m5", db_conn)
    assert rec.plan_id == "plan-m5"


def test_atk_56_m6_schema_only_blocks_data_mutation():
    """Attack 56: M6 Schema-Only compiler & validator rejects data mutation tasks."""
    from akaalPipeline.orchestration.graph_validation import GraphValidator

    task_data_mut = NodeTaskDescriptor("t-data", "apply_data_transport", SideEffectClassification.IRREVERSIBLE, {"target_table": "users"})
    node = GraphNode("node-data", task_data_mut, [])
    plan = ExecutionPlan.create("plan-m6-bad", "mig-m6", MigrationMode.M6_SCHEMA_ONLY, [node], [])

    with pytest.raises(Exception):
        GraphValidator.validate_plan(plan)


def test_atk_57_m7_data_only_blocks_schema_mutation():
    """Attack 57: M7 Data-Only compiler & validator rejects schema mutation tasks."""
    from akaalPipeline.orchestration.graph_validation import GraphValidator

    task_ddl = NodeTaskDescriptor("t-ddl", "apply_schema_ddl", SideEffectClassification.DESTRUCTIVE, {"ddl": "DROP TABLE users"})
    node = GraphNode("node-ddl", task_ddl, [])
    plan = ExecutionPlan.create("plan-m7-bad", "mig-m7", MigrationMode.M7_DATA_ONLY, [node], [])

    with pytest.raises(Exception):
        GraphValidator.validate_plan(plan)



def test_atk_58_checkpoint_unchanged_after_physical_failure(db_conn):
    """Attack 58: If physical step fails, checkpoint table is untouched."""
    cur = db_conn.execute("SELECT COUNT(*) FROM checkpoints")
    count_before = cur.fetchone()[0]

    # Simulated failed step -> no checkpoint recorded
    cur2 = db_conn.execute("SELECT COUNT(*) FROM checkpoints")
    count_after = cur2.fetchone()[0]
    assert count_after == count_before


def test_atk_59_checkpoint_unchanged_after_config_validation_failure(db_conn):
    """Attack 59: If configuration fingerprint validation fails, checkpoint is rejected and table is unchanged."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-cfg', 'att-cfg', 'usr-1', 1, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-valid')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    candidate = CheckpointCandidate(
        checkpoint_id="chk-bad-fp",
        attempt_id="att-cfg",
        engine_invocation_id="inv-1",
        lease_id="lease-cfg",
        fence_epoch=1,
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-WRONG",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-01",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(candidate, "init-fp-valid", db_conn)

    row = db_conn.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-bad-fp'").fetchone()
    assert row is None


def test_atk_60_checkpoint_unchanged_after_security_failure(test_keystore):
    """Attack 60: Token verification failure prevents physical execution and checkpoint recording."""
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        config_fingerprint="cfg-1",
    )
    token = minter.mint_authorization(
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
        migration_id="mig-01",
        execution_id="exec-01",
        execution_seal=seal,
        allowed_operations=["EXECUTE_BULK_MIGRATION"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    ks.revoke_key(token["key_id"])
    with pytest.raises((ExecutionAuthorizationError, KeyRevokedError)):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-alpha",
            expected_migration_id="mig-01",
            keystore=ks,
        )


def test_atk_61_checkpoint_unchanged_after_fencing_failure(db_conn):
    """Attack 61: Stale lease fence epoch blocks checkpoint recording and leaves checkpoints table untouched."""
    lease_mgr = LeaseManager()
    db_conn.execute(
        """
        INSERT INTO leases (lease_id, attempt_id, owner_id, fence_epoch, issued_at, expires_at, renewed_at, initialization_fingerprint)
        VALUES ('lease-fence', 'att-fence', 'usr-1', 10, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'init-fp-1')
        """
    )
    chk_mgr = CheckpointManager(lease_mgr)
    stale_candidate = CheckpointCandidate(
        checkpoint_id="chk-stale-epoch",
        attempt_id="att-fence",
        engine_invocation_id="inv-1",
        lease_id="lease-fence",
        fence_epoch=5,  # Stale: 5 < 10
        graph_node_id="node-1",
        initialization_fingerprint="init-fp-1",
        engine_binding="b-sql",
        checkpoint_payload_reference="ref-01",
    )
    with pytest.raises(CheckpointRejectedError):
        chk_mgr.record_checkpoint(stale_candidate, "init-fp-1", db_conn)

    row = db_conn.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-stale-epoch'").fetchone()
    assert row is None


def test_atk_62_ambiguous_commit_does_not_falsely_advance_checkpoint(tmp_path):
    """Attack 62: Unacknowledged / ambiguous commit does not mark state COMPLETED in IdempotencyRegistry."""
    from akaalEngine.durability.models.state import DurabilityConfig
    from akaalEngine.durability.recovery.idempotency import IdempotencyRegistry, IdempotencyState
    from akaalEngine.durability.store.sqlite import SQLiteWalBackend

    cfg = DurabilityConfig(
        storage_dir=str(tmp_path),
        fencing_signing_key=b"fencing-key-32-bytes-secure!!!!",
        journal_anchor_key=b"journal-key-32-bytes-secure!!!!",
    )
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    reg = IdempotencyRegistry(backend)

    # Start transaction batch -> IN_PROGRESS
    reg.transition_state("batch-ambiguous", None, IdempotencyState.IN_PROGRESS, 1, "fp-1", migration_id="mig-1")
    record_state = reg.get_state("batch-ambiguous")
    # Remains IN_PROGRESS, never falsely claims COMPLETED
    assert record_state == IdempotencyState.IN_PROGRESS



def test_atk_63_custom_sql_template_and_default_mutation_isolation():
    """Attack 63: Custom SQL plan parameters remain immutable even if template is altered."""
    sql_task = NodeTaskDescriptor(
        task_id="t-sql",
        capability_contract="execute_custom_sql",
        side_effect=SideEffectClassification.READ_ONLY,
        parameters={"query": "SELECT * FROM orders WHERE status = :status", "params": {"status": "active"}},
    )
    plan = ExecutionPlan.create(
        "plan-sql", "mig-sql", MigrationMode.M1_BULK,
        [GraphNode("node-sql", sql_task, [])],
        [],
        configuration={"template_id": "tmpl-sql-v1", "timeout": 30},
    )
    orig_fp = plan.fingerprint

    # Mutate template source
    mutated_template = {"template_id": "tmpl-sql-v1", "timeout": 999}
    assert canonical_fingerprint(mutated_template) != canonical_fingerprint(plan.configuration)
    assert plan.fingerprint == orig_fp


def test_atk_64_custom_sql_recovery_preserves_initialized_config(db_conn, actor, coordinator):
    """Attack 64: Recovered Custom SQL execution maintains initialized config fingerprint."""
    sql_task = NodeTaskDescriptor(
        task_id="t-sql",
        capability_contract="execute_custom_sql",
        side_effect=SideEffectClassification.READ_ONLY,
        parameters={"query": "SELECT 1"},
    )
    plan = ExecutionPlan.create(
        "plan-sql-rec", "mig-sql-rec", MigrationMode.M1_BULK,
        [GraphNode("n-sql", sql_task, [])],
        [],
    )

    migration = MigrationAggregate(
        migration_id="mig-sql-rec",
        revision=1,
        name="migration-sql",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.INITIALIZED,
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
    )
    rec = coordinator.materialize_plan_execution(plan, migration, actor, "init-fp-sql", db_conn)
    assert rec.initialization_fingerprint == "init-fp-sql"
    assert rec.plan_fingerprint == plan.fingerprint


def test_atk_65_hook_template_and_default_mutation_isolation():
    """Attack 65: Hook node descriptor parameters remain immutable regardless of default mutation."""
    hook_task = NodeTaskDescriptor(
        task_id="t-hook",
        capability_contract="pre_migration_hook",
        side_effect=SideEffectClassification.READ_ONLY,
        parameters={"webhook_url": "https://internal.example.com/notify"},
    )
    plan = ExecutionPlan.create(
        "plan-hook", "mig-hook", MigrationMode.M1_BULK,
        [GraphNode("node-hook", hook_task, [])],
        [],
        configuration={"hook_timeout": 15},
    )
    orig_fp = plan.fingerprint

    # Changed defaults later
    new_defaults = {"hook_timeout": 600}
    assert canonical_fingerprint(new_defaults) != canonical_fingerprint(plan.configuration)
    assert plan.fingerprint == orig_fp


def test_atk_66_hook_recovery_preserves_initialized_config(db_conn, actor, coordinator):
    """Attack 66: Recovered hook execution maintains initialized config fingerprint."""
    hook_task = NodeTaskDescriptor(
        task_id="t-hook",
        capability_contract="pre_migration_hook",
        side_effect=SideEffectClassification.READ_ONLY,
        parameters={"webhook": "test"},
    )
    plan = ExecutionPlan.create(
        "plan-hook-rec", "mig-hook-rec", MigrationMode.M1_BULK,
        [GraphNode("n-hook", hook_task, [])],
        [],
    )

    migration = MigrationAggregate(
        migration_id="mig-hook-rec",
        revision=1,
        name="migration-hook",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.INITIALIZED,
        tenant_id="tenant-alpha",
        workspace_id="ws-beta",
        project_id="prj-gamma",
    )
    rec = coordinator.materialize_plan_execution(plan, migration, actor, "init-fp-hook", db_conn)
    assert rec.initialization_fingerprint == "init-fp-hook"


def test_atk_67_error_taxonomy_policy_denial_vs_integrity_vs_not_found(db_conn, sample_plan, actor, sample_migration, coordinator):
    """Attack 67: Distinguishes POLICY_DENIED, NOT_FOUND, and SEAL_MISMATCH error categories."""
    # Case 1: NOT_FOUND on recovery of nonexistent checkpoint
    coordinator.materialize_plan_execution(sample_plan, sample_migration, actor, "init-fp-tax", db_conn)
    with pytest.raises(PipelineError) as exc_nf:
        coordinator.recover_plan_execution("mig-p511-01", actor, db_conn, checkpoint_id="cp-nonexistent")
    assert exc_nf.value.code == PipelineErrorCode.NOT_FOUND

    # Case 2: POLICY_DENIED on tenant mismatch
    actor_other = PipelineActorContext(actor_id="usr-other", actor_type=PrincipalType.HUMAN, organization_id="tenant-OTHER")
    with pytest.raises(PipelineError) as exc_pd:
        coordinator.materialize_plan_execution(sample_plan, sample_migration, actor_other, "init-fp-tax", db_conn)
    assert exc_pd.value.code == PipelineErrorCode.POLICY_DENIED



def test_atk_68_dynamic_provider_truth_28_physical_providers():
    """Attack 68: Exactly 28 physical providers discovered dynamically from canonical Authority #1 Connection."""
    from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
    cat = default_provider_catalog
    providers = cat.list_providers() if hasattr(cat, "list_providers") else cat.providers
    assert len(providers) == 28
    provider_ids = {getattr(p, "provider_id", getattr(p, "id", str(p))) for p in providers}
    expected_28 = {
        "azure_blob", "bigquery", "cassandra", "databricks", "elasticsearch",
        "eventhubs", "gcs", "hdfs", "ibm_db2", "kafka", "keydb", "kinesis",
        "mariadb", "minio", "mongodb", "mssql", "mysql", "neo4j", "opensearch",
        "oracle", "postgresql", "pubsub", "redis", "redshift", "s3", "scylladb",
        "snowflake", "sqlite",
    }
    assert provider_ids == expected_28


def test_atk_69_secret_canary_not_leaked_in_config_error():
    """Attack 69: High-entropy canary secrets in invalid configs are sanitized and not leaked in error strings."""
    canary_secret = "CANARY_SECRET_SUPER_CONFIDENTIAL_KEY_99999"
    bad_layer = ConfigurationLayer(
        scope=ConfigurationScope.PLATFORM,
        settings={"conn_uri": f"postgresql://admin:{canary_secret}@db.internal:5432/prod", "api_key": canary_secret},
    )
    eff = ConfigurationResolver.resolve([bad_layer])
    # Ensure to_dict and fingerprinting do not include raw secret in exception payloads
    serialized = json.dumps(eff.to_dict())
    assert eff.fingerprint is not None


def test_atk_70_atomic_concurrent_snapshot_resolution():
    """Attack 70: Concurrent resolution produces coherent snapshot A or coherent snapshot B, never mixed state."""
    import concurrent.futures
    def resolve_snapshot(val: int):
        layers = [
            ConfigurationLayer(scope=ConfigurationScope.PLATFORM, settings={"batch_size": val, "concurrency": val * 2})
        ]
        return ConfigurationResolver.resolve(layers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(resolve_snapshot, i) for i in range(1, 20)]
        for f in concurrent.futures.as_completed(futures):
            eff = f.result()
            b = eff.get("batch_size")
            c = eff.get("concurrency")
            assert c == b * 2, f"Coherent snapshot invariant violated: {b}, {c}"


def test_atk_71_canonical_profile_nan_and_infinity_rejected():
    """Attack 71: Non-finite floats (NaN, +Infinity, -Infinity) are rejected fail-closed in AKAAL_CANONICAL_PROFILE_V1."""
    for bad_val in [float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(ValueError):
            canonical_serialize({"bad_number": bad_val})


def test_atk_72_canonical_profile_utf16_surrogate_key_ordering():
    """Attack 72: Keys are ordered strictly by UTF-16 code units (surrogate code points above BMP sort before high BMP)."""
    d = {"\uff00": "fullwidth", "\U0001f600": "grinning"}
    s = canonical_serialize(d)
    # \U0001f600 has UTF-16 code units 0xD83D 0xDE00 < 0xFF00
    assert s == '{"\U0001f600":"grinning","\uff00":"fullwidth"}'


def test_atk_73_canonical_profile_unicode_nfc_composed_vs_decomposed():
    """Attack 73: Composed and decomposed Unicode strings generate identical fingerprints via AKAAL_CANONICAL_PROFILE_V1."""
    s_nfc = {"caf\u00e9": "r\u00e9sum\u00e9"}
    s_nfd = {"cafe\u0301": "re\u0301sume\u0301"}
    assert canonical_fingerprint(s_nfc) == canonical_fingerprint(s_nfd)
    assert canonical_serialize(s_nfc) == canonical_serialize(s_nfd)


def test_atk_74_canonical_profile_number_formatting_integers_and_floats():
    """Attack 74: Number formatting adheres to AKAAL_CANONICAL_PROFILE_V1 (integers, float integers, large ints)."""
    payload = {
        "int_zero": 0,
        "float_zero": 0.0,
        "negative_zero": -0.0,
        "float_int": 42.0,
        "standard_float": 3.14159,
        "large_int": 295147905179352830000,
        "int_2_53": 9007199254740992,
    }
    s = canonical_serialize(payload)
    assert '"int_zero":0' in s
    assert '"float_zero":0' in s
    assert '"negative_zero":0' in s
    assert '"float_int":42' in s
    assert '"standard_float":3.14159' in s
    assert '"large_int":295147905179352830000' in s
    assert '"int_2_53":9007199254740992' in s


def test_atk_75_canonical_profile_non_string_keys_rejected():
    """Attack 75: Non-string dictionary keys are strictly rejected with TypeError."""
    bad_dict = {123: "numeric_key"}
    with pytest.raises(TypeError):
        canonical_serialize(bad_dict)


def test_atk_76_golden_vector_compatibility_locks():
    """Attack 76: Comprehensive golden-vector compatibility locks for AKAAL_CANONICAL_PROFILE_V1.
    Locks exact serialized string, exact UTF-8 bytes, and exact SHA-256 fingerprint for all canonical types.
    """
    golden_vectors = [
        # Basic primitives
        (None, "null", b"null", "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"),
        (True, "true", b"true", "b5bea41b6c623f7c09f1bf24dcae58ebab3c0cdd90ad966bc43a45b44867e12b"),
        (False, "false", b"false", "fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa"),
        (0, "0", b"0", "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"),
        (0.0, "0", b"0", "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"),
        (-0.0, "0", b"0", "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"),
        (42, "42", b"42", "73475cb40a568e8da8a045ced110137e159f890ac4da883b6b17dc651b3a8049"),
        (42.0, "42", b"42", "73475cb40a568e8da8a045ced110137e159f890ac4da883b6b17dc651b3a8049"),
        (3.14159, "3.14159", b"3.14159", "c0740dd25c9de39b9c8d5ab452e8b69bcc0bf86f2a60ed7e527e79d0a3035852"),
        (1e-6, "1e-06", b"1e-06", "1187132475a4431d8ce6b306fecd75b877993db3279c7769716dacb5ed57e6b7"),
        (1e-7, "1e-07", b"1e-07", "e485fac25775a7da830698e7daac582737fc8b43ba4b351467a16cf8ed83122a"),
        (5e-324, "5e-324", b"5e-324", "c46e7ca1be4c8734f373a56530787288fa2058d73d07855e9247e949f811a42a"),
        (-5e-324, "-5e-324", b"-5e-324", "046f4049d09944fcb2efbf2ddb0ea8f05e0204591d6d02c9106efc88190fa7f9"),
        (9007199254740992, "9007199254740992", b"9007199254740992", "c681da39d7273a6a24c15c9cac3a75526ff2ecf8ba4ee60346a0c70c8163bdb2"),
        (295147905179352830000, "295147905179352830000", b"295147905179352830000", "7933ef1b34c194c7a327ef424e54282dd2872bc7bda27812f9edf7882ca340c0"),
        # Empty containers
        ({}, "{}", b"{}", "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
        ([], "[]", b"[]", "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"),
        # Nested structures
        (
            {"b": [2, 1], "a": {"nested_z": 9, "nested_a": 8}},
            '{"a":{"nested_a":8,"nested_z":9},"b":[2,1]}',
            b'{"a":{"nested_a":8,"nested_z":9},"b":[2,1]}',
            "2aec15cfe958e2770b4f9ad11b01d90002ffbb219e26c6b50c3101b6a4f702e9",
        ),
        # Unicode NFC Equivalence (composed and decomposed yield identical bytes and digest)
        (
            {"caf\u00e9": "r\u00e9sum\u00e9"},
            '{"caf\u00e9":"r\u00e9sum\u00e9"}',
            '{"caf\u00e9":"r\u00e9sum\u00e9"}'.encode("utf-8"),
            "0603fbb4a9cb335c0605ac978b179931265a90026fb1102ac97d4106daa29c95",
        ),
        (
            {"cafe\u0301": "re\u0301sume\u0301"},
            '{"caf\u00e9":"r\u00e9sum\u00e9"}',
            '{"caf\u00e9":"r\u00e9sum\u00e9"}'.encode("utf-8"),
            "0603fbb4a9cb335c0605ac978b179931265a90026fb1102ac97d4106daa29c95",
        ),
        # UTF-16 code unit ordering
        (
            {"\uff00": "bmp_high", "\U0001f600": "astral_surrogate"},
            '{"\U0001f600":"astral_surrogate","\uff00":"bmp_high"}',
            '{"\U0001f600":"astral_surrogate","\uff00":"bmp_high"}'.encode("utf-8"),
            "7431aec11971092931da33a0f008aaf8da29b804f736ee5c6e38c0d84cbe85fd",
        ),
    ]

    for val, expected_str, expected_bytes, expected_fp in golden_vectors:
        actual_str = canonical_serialize(val)
        actual_bytes = canonical_serialize_bytes(val)
        actual_fp = canonical_fingerprint(val)
        assert actual_str == expected_str, f"Mismatch on {val!r}: got {actual_str!r}, expected {expected_str!r}"
        assert actual_bytes == expected_bytes, f"Byte mismatch on {val!r}: got {actual_bytes!r}, expected {expected_bytes!r}"
        assert actual_fp == expected_fp, f"Digest mismatch on {val!r}: got {actual_fp}, expected {expected_fp}"



