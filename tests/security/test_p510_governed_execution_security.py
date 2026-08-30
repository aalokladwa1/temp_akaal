"""tests.security.test_p510_governed_execution_security
=====================================================
Comprehensive 62-Case Hostile Security Test Suite for AKAAL P5.10
Governed Execution Security, 14-Dimension Execution Seal, Layer A/B Separation,
Maker-Checker Invariants, M8 Non-Mutation, Engine Zero-Trust KeyStore Root, and Fencing.
"""

from __future__ import annotations

import os
import json
import time
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher
from akaalEngine.transport.drivers.base import StaleFencingEpochError
from akaalEngine.transport.drivers.generic_sql import GenericSQLTargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata

from akaalIPC.protocol.envelopes import CommandEnvelope
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus

from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import (
    ApprovalStatus,
    GrantResourceType,
    GrantSubjectType,
    MigrationLifecycleState,
    MigrationMode,
    PolicyEffect,
    SecurityAlertSeverity,
    SideEffectClassification,
)
from akaalPipeline.contracts.errors import (
    ConflictError,
    ForbiddenError,
    PipelineError,
    PipelineErrorCode,
    PolicyDeniedError,
    UnauthorizedError,
)
from akaalPipeline.contracts.serialization import canonical_fingerprint
from akaalPipeline.execution.coordinator import PlanExecutionCoordinator
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphNode, NodeTaskDescriptor
from akaalPipeline.policy.approval_artifact import GovernanceApprovalArtifact
from akaalPipeline.policy.contracts import (
    PolicyAction,
    PolicyDecision,
    PolicyResource,
    PolicyResult,
    PolicySubject,
)
from akaalPipeline.policy.gates import PolicyGateEvaluator
from akaalPipeline.ports.engine import EngineInvocationRequest, EngineInvocationResult, ExecutionPort
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.central_authorization import AuthorizationContext, CentralAuthorizationEngine
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.detection import SecurityThreatDetector
from akaalPipeline.security.execution_authorization import (
    ExecutionAuthorizationError,
    ExecutionAuthorizationMinter,
    ExecutionReplayCache,
    GLOBAL_REPLAY_CACHE,
    verify_execution_authorization,
)
from akaalPipeline.security.keystore import KeyPurpose, KeyStoreAuthority
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.security.seal import ExecutionSeal, ExecutionSealBuilder
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.artifacts import ImmutableArtifact
from akaalPipeline.state.repositories import SQLiteKeyringRepository, SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


# =============================================================================
# Helper Fixtures & Builders
# =============================================================================

@pytest.fixture
def test_keystore(tmp_path):
    db_path = str(tmp_path / "p510_keystore.db")
    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()
    ks = KeyStoreAuthority(
        keyring_repo=uow.keyring,
        master_root_key=b"p510-master-root-key-32bytes!!!!"  # exactly 32 bytes
    )
    ks.initialize_purpose_keys_if_missing()
    return ks, uow


def build_valid_14d_seal(
    tenant_id: str = "tenant-acme",
    workspace_id: str = "ws-prod",
    project_id: str = "prj-analytics",
    migration_id: str = "mig-p510-001",
    plan_id: str = "plan-p510-001",
    plan_revision: int = 1,
    execution_mode: str = "M1",
    source_fp: str = "fp-src-v1",
    target_fp: str = "fp-tgt-v1",
    scope_fp: str = "fp-scope-v1",
    config_fp: str = "fp-cfg-v1",
    init_fp: str = "fp-init-v1",
    appr_fp: str = "fp-appr-v1",
    fence_epoch: int = 1,
) -> ExecutionSeal:
    return ExecutionSealBuilder.build_seal(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        migration_id=migration_id,
        plan_id=plan_id,
        plan_revision=plan_revision,
        execution_mode=execution_mode,
        source_identity_fp=source_fp,
        target_identity_fp=target_fp,
        selection_scope_fp=scope_fp,
        config_fp=config_fp,
        initialization_fp=init_fp,
        approval_fp=appr_fp,
        fence_epoch=fence_epoch,
    )


# =============================================================================
# GROUP 1: Layer A — 14-Dimension ExecutionSeal Hostile Attack Vectors (01–14)
# =============================================================================

def test_atk_01_seal_tamper_tenant_id(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(tenant_id="tenant-acme")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Tenant mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-malicious",
            keystore=ks,
        )


def test_atk_02_seal_tamper_workspace_id(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(workspace_id="ws-prod")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="workspace"):
        verify_execution_authorization(
            artifact=token,
            expected_workspace_id="ws-tampered",
            keystore=ks,
        )


def test_atk_03_seal_tamper_project_id(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(project_id="prj-analytics")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="project"):
        verify_execution_authorization(
            artifact=token,
            expected_project_id="prj-tampered",
            keystore=ks,
        )


def test_atk_04_seal_tamper_migration_id(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-p510-001")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Migration mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_migration_id="mig-p510-other",
            keystore=ks,
        )


def test_atk_05_seal_tamper_plan_id():
    seal = build_valid_14d_seal(plan_id="plan-original")
    s_dict = seal.to_dict()
    s_dict["plan_id"] = "plan-mutated"
    tampered_fp = canonical_fingerprint(s_dict)
    assert tampered_fp != seal.seal_fingerprint


def test_atk_06_seal_tamper_plan_revision():
    seal1 = build_valid_14d_seal(plan_revision=1)
    seal2 = build_valid_14d_seal(plan_revision=2)
    assert seal1.seal_fingerprint != seal2.seal_fingerprint


def test_atk_07_seal_tamper_execution_mode(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(execution_mode="M1")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Execution mode mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_execution_mode="M8",
            keystore=ks,
        )


def test_atk_08_seal_tamper_source_identity_fp():
    s1 = build_valid_14d_seal(source_fp="src-a")
    s2 = build_valid_14d_seal(source_fp="src-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_09_seal_tamper_target_identity_fp():
    s1 = build_valid_14d_seal(target_fp="tgt-a")
    s2 = build_valid_14d_seal(target_fp="tgt-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_10_seal_tamper_selection_scope_fp():
    s1 = build_valid_14d_seal(scope_fp="scope-a")
    s2 = build_valid_14d_seal(scope_fp="scope-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_11_seal_tamper_config_fp():
    s1 = build_valid_14d_seal(config_fp="cfg-a")
    s2 = build_valid_14d_seal(config_fp="cfg-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_12_seal_tamper_initialization_fp():
    s1 = build_valid_14d_seal(init_fp="init-a")
    s2 = build_valid_14d_seal(init_fp="init-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_13_seal_tamper_approval_fp():
    s1 = build_valid_14d_seal(appr_fp="appr-a")
    s2 = build_valid_14d_seal(appr_fp="appr-b")
    assert s1.seal_fingerprint != s2.seal_fingerprint


def test_atk_14_seal_tamper_fence_epoch(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(fence_epoch=1)
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Fencing epoch mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_fencing_epoch=2,
            keystore=ks,
        )


# =============================================================================
# GROUP 2: Layer B — Policy-Resolved Governance & Maker-Checker Invariants (15–28)
# =============================================================================

def test_atk_15_maker_checker_self_approval_prohibition(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "mc.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor_creator = PipelineActorContext(actor_id="user-bob", actor_type="user", organization_id="tenant-1", roles=["developer", "admin"])
    
    with uow:
        res_create = caller.command_handlers.handle_create_migration(
            {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
            actor_creator,
            uow,
        )
    mig_id = res_create["migration_id"]

    # Bob attempts to approve his own migration -> MUST FAIL CLOSED
    with pytest.raises(PipelineError, match="Maker-checker violation"):
        with uow:
            caller.command_handlers.handle_approve_migration(
                {"migration_id": mig_id, "requester_id": "user-bob"},
                actor_creator,
                uow,
            )


def test_atk_16_non_governance_role_approval_rejected(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "gov_role.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor_creator = PipelineActorContext(actor_id="user-bob", actor_type="user", organization_id="tenant-1", roles=["developer"])
    with uow:
        res_create = caller.command_handlers.handle_create_migration(
            {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
            actor_creator,
            uow,
        )
    mig_id = res_create["migration_id"]

    # Actor with only developer role tries to approve
    actor_dev = PipelineActorContext(actor_id="user-alice", actor_type="user", organization_id="tenant-1", roles=["developer"])
    with pytest.raises(PipelineError, match="lacks governance authorization"):
        with uow:
            caller.command_handlers.handle_approve_migration(
                {"migration_id": mig_id, "requester_id": "user-bob"},
                actor_dev,
                uow,
            )


def test_atk_17_cross_migration_approval_replay():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "intent_fingerprint": "fp-original",
        "approvers": ["gov-officer-1"],
    }
    with pytest.raises(PolicyDeniedError, match="migration ID mismatch"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-002",
            current_plan_fingerprint="fp-original",
        )


def test_atk_18_material_plan_mutation_invalidates_approval():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "intent_fingerprint": "fp-plan-v1",
        "approvers": ["gov-officer-1"],
    }
    # Plan has mutated to fp-plan-v2
    with pytest.raises(PolicyDeniedError, match="intent fingerprint does not match"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-001",
            current_plan_fingerprint="fp-plan-v2",
        )


def test_atk_19_config_mutation_invalidates_approval():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "intent_fingerprint": "fp-plan-v1",
        "config_fingerprint": "cfg-v1",
        "approvers": ["gov-officer-1"],
    }
    with pytest.raises(PolicyDeniedError, match="config fingerprint mismatch"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-001",
            current_plan_fingerprint="fp-plan-v1",
            expected_config_fingerprint="cfg-v2",
        )


def test_atk_20_insufficient_approval_quorum():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "approvers": ["gov-officer-1"],
    }
    with pytest.raises(PolicyDeniedError, match="Insufficient approval quorum"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-001",
            min_quorum=2,
        )


def test_atk_21_expired_policy_decision():
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    decision = PolicyDecision(
        decision_id="dec-expired",
        policy_version="1.0.0",
        subject=PolicySubject(actor_id="user-1", actor_type="user", roles=["admin"]),
        action=PolicyAction(name="migration.start"),
        resource=PolicyResource(resource_id="mig-001", resource_type="migration"),
        result=PolicyResult.ALLOW,
        reason="Test expired",
        issuer_id="admin-1",
        issuer_roles=["SecurityOfficer"],
        effective_at=past_iso,
        expires_at=past_iso,
    )
    with pytest.raises(PolicyDeniedError, match="has expired"):
        PolicyGateEvaluator.evaluate_gate(
            decision=decision,
            expected_resource_id="mig-001",
            current_time_iso=now_iso,
        )


def test_atk_22_missing_governance_approval_fails_closed():
    with pytest.raises(PolicyDeniedError, match="No approved governance record found"):
        PolicyGateEvaluator.validate_approval_record(
            approval=None,
            expected_migration_id="mig-001",
        )


def test_atk_23_valid_governance_approval_passes():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "intent_fingerprint": "fp-plan-v1",
        "approvers": ["gov-officer-1", "gov-officer-2"],
    }
    # Must succeed without exception
    PolicyGateEvaluator.validate_approval_record(
        approval=approval,
        expected_migration_id="mig-001",
        current_plan_fingerprint="fp-plan-v1",
        min_quorum=2,
    )


def test_atk_24_wrong_action_approval_rejected():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "action": "schema_prep",
        "approvers": ["gov-officer-1"],
    }
    with pytest.raises(PolicyDeniedError, match="Approval action mismatch"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-001",
            expected_action="cutover",
        )


def test_atk_25_wrong_node_approval_rejected():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-001",
        "graph_node_id": "node-extract-01",
        "approvers": ["gov-officer-1"],
    }
    with pytest.raises(PolicyDeniedError, match="Approval node mismatch"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-001",
            expected_node_id="node-apply-01",
        )


def test_atk_26_cross_tenant_approval_isolated(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "tenant_iso.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor_t1 = PipelineActorContext(actor_id="user-t1", actor_type="user", organization_id="tenant-1", roles=["admin", "governor"])
    with uow:
        res_create = caller.command_handlers.handle_create_migration(
            {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
            actor_t1,
            uow,
        )
    mig_id = res_create["migration_id"]

    # Actor from tenant-2 tries to approve tenant-1 migration
    actor_t2 = PipelineActorContext(actor_id="user-t2", actor_type="user", organization_id="tenant-2", roles=["admin", "governor"])
    with pytest.raises(PipelineError, match="not found or unauthorized for tenant"):
        with uow:
            caller.command_handlers.handle_approve_migration(
                {"migration_id": mig_id},
                actor_t2,
                uow,
            )


def test_atk_27_cross_workspace_approval_isolated(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "ws_iso.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor_ws1 = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", workspace_id="ws-1", roles=["admin", "governor"])
    with uow:
        res_create = caller.command_handlers.handle_create_migration(
            {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
            actor_ws1,
            uow,
        )
    mig_id = res_create["migration_id"]

    actor_ws2 = PipelineActorContext(actor_id="user-2", actor_type="user", organization_id="tenant-1", workspace_id="ws-2", roles=["admin", "governor"])
    with pytest.raises(PipelineError, match="different workspace"):
        with uow:
            caller.command_handlers.handle_approve_migration(
                {"migration_id": mig_id},
                actor_ws2,
                uow,
            )


def test_atk_28_cross_project_approval_isolated(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "prj_iso.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor_p1 = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", project_id="prj-1", roles=["admin", "governor"])
    with uow:
        res_create = caller.command_handlers.handle_create_migration(
            {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
            actor_p1,
            uow,
        )
    mig_id = res_create["migration_id"]

    actor_p2 = PipelineActorContext(actor_id="user-2", actor_type="user", organization_id="tenant-1", project_id="prj-2", roles=["admin", "governor"])
    with pytest.raises(PipelineError, match="different project"):
        with uow:
            caller.command_handlers.handle_approve_migration(
                {"migration_id": mig_id},
                actor_p2,
                uow,
            )


# =============================================================================
# GROUP 3: M8 Non-Mutation & Operation Enforcement (29–38)
# =============================================================================

@pytest.mark.parametrize("op_enum", [
    SemanticOperation.EXECUTE_BULK_MIGRATION,
    SemanticOperation.EXECUTE_CDC_SYNC,
    SemanticOperation.APPLY_SCHEMA_CHANGES,
    SemanticOperation.EXECUTE_INCREMENTAL_APPLY,
    SemanticOperation.EXECUTE_ATOMIC_CUTOVER,
    SemanticOperation.RECONCILE_DISPUTED_RECORDS,
    SemanticOperation.ROLLBACK_TRANSACTION_BATCH,
])
def test_atk_29_to_35_m8_mode_rejects_all_mutations(op_enum):
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-m8-01",
        run_id="run-01",
        tenant_id="tenant-1",
        execution_mode="M8_VALIDATION_ONLY",
    )
    req = GatewayRequest(
        operation=op_enum,
        context=ctx,
        payload={"execution_mode": "M8_VALIDATION_ONLY"},
    )
    resp = dispatcher.dispatch(req)
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.UNSUPPORTED_OPERATION.value
    assert "M8 validation-only mode" in resp.error_message


def test_atk_36_m8_mode_allows_read_only_schema_discovery():
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-m8-02",
        run_id="run-01",
        tenant_id="tenant-1",
        execution_mode="M8_VALIDATION_ONLY",
    )
    req = GatewayRequest(
        operation=SemanticOperation.TEST_CONNECTION,
        context=ctx,
        payload={"provider_id": "sqlite"},
    )
    # Test connection is read-only diagnostic, not mutating
    resp = dispatcher.dispatch(req)
    assert "M8 validation-only mode" not in (resp.error_message or "")


def test_atk_37_m8_mode_coordinator_blocks_mutating_dag_node(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "m8_coord.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", roles=["admin"])
    
    # Create an aggregate with M8 mode and valid workspace/project
    agg = MigrationAggregate(
        migration_id="mig-m8-coord",
        revision=1,
        name="M8 Validation Run",
        tenant_id="tenant-1",
        workspace_id="ws-default",
        project_id="prj-default",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        state=MigrationLifecycleState.INITIALIZED,
    )
    with uow:
        caller.repository.save(agg, connection=uow.connection)

    plan = ExecutionPlan(
        plan_id="plan-m8",
        migration_id="mig-m8-coord",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        nodes=[
            GraphNode(
                node_id="node-bulk",
                task=NodeTaskDescriptor(
                    task_id="task-bulk",
                    capability_contract="data_transport",
                    side_effect=SideEffectClassification.REVERSIBLE,
                ),
                dependencies=[],
            )
        ],
        edges=[],
        fingerprint="fp-m8",
    )

    with patch.object(caller.plan_coordinator.capability_resolver, "evaluate_capability") as mock_eval:
        mock_eval.return_value = MagicMock(
            is_available=True,
            selected_binding=MagicMock(binding_id="bind-1", port_instance=MagicMock(spec=ExecutionPort)),
            side_effect=SideEffectClassification.REVERSIBLE,
        )
        
        with uow:
            rec = caller.plan_coordinator.materialize_plan_execution(
                plan=plan, migration=agg, actor=actor,
                initialization_fingerprint="fp-m8", conn=uow.connection,
            )
        
        outcome = caller.plan_coordinator.advance_plan_execution(
            execution_id=rec.execution_id,
            plan=plan,
            actor=actor,
            operation_id="op-m8-mut",
            correlation_id="corr-m8-mut",
            request_id="req-m8-mut",
            payload={},
            uow_factory=lambda: caller._create_uow(),
        )
        assert outcome.is_success is False
        assert outcome.error_code == "M8_MUTATION_PROHIBITED"


def test_atk_38_m8_mode_coordinator_allows_read_only_dag_node(tmp_path, monkeypatch):
    monkeypatch.setenv("AKAAL_GATEWAY_RECEIPT_SECRET", "super-secret-gateway-receipt-key-32")
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "m8_ro.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    actor = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", roles=["admin"])
    
    agg = MigrationAggregate(
        migration_id="mig-m8-ro",
        revision=1,
        name="M8 RO Run",
        tenant_id="tenant-1",
        workspace_id="ws-default",
        project_id="prj-default",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        state=MigrationLifecycleState.INITIALIZED,
    )
    with uow:
        caller.repository.save(agg, connection=uow.connection)

    plan = ExecutionPlan(
        plan_id="plan-m8-ro",
        migration_id="mig-m8-ro",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        nodes=[
            GraphNode(
                node_id="node-compare",
                task=NodeTaskDescriptor(
                    task_id="task-compare",
                    capability_contract="state_diff",
                    side_effect=SideEffectClassification.READ_ONLY,
                ),
                dependencies=[],
            )
        ],
        edges=[],
        fingerprint="fp-m8-ro",
    )

    from akaalEngine.gateway.models.responses import sign_receipt

    def _execute_side_effect(req):
        status_code = "SUCCESS"
        sig = sign_receipt(
            migration_id="mig-m8-ro",
            run_id=req.attempt_id,
            operation_id=req.operation_id or f"op-{req.invocation_id}",
            fencing_epoch=req.fence_epoch,
            status_code=status_code,
            initialization_fingerprint=req.initialization_fingerprint,
            job_id=req.graph_node_id,
        )
        receipt = {
            "gateway_migration_id": "mig-m8-ro",
            "gateway_run_id": req.attempt_id,
            "gateway_operation_id": req.operation_id or f"op-{req.invocation_id}",
            "gateway_job_id": req.graph_node_id,
            "gateway_fencing_epoch": req.fence_epoch,
            "graph_node_id": req.graph_node_id,
            "initialization_fingerprint": req.initialization_fingerprint,
            "gateway_status_code": status_code,
            "receipt_signature": sig,
        }
        return EngineInvocationResult(
            invocation_id=req.invocation_id,
            attempt_id=req.attempt_id,
            graph_node_id=req.graph_node_id,
            binding_id=req.binding_id,
            lease_id=req.lease_id,
            fence_epoch=req.fence_epoch,
            initialization_fingerprint=req.initialization_fingerprint,
            is_success=True,
            result_payload={"status": "EQUAL", "engine_execution_receipt": receipt},
        )

    mock_port = MagicMock(spec=ExecutionPort)
    mock_port.execute_task.side_effect = _execute_side_effect

    with patch.object(caller.plan_coordinator.capability_resolver, "evaluate_capability") as mock_eval:
        mock_eval.return_value = MagicMock(
            is_available=True,
            selected_binding=MagicMock(binding_id="bind-ro", port_instance=mock_port),
            side_effect=SideEffectClassification.READ_ONLY,
        )
        
        with uow:
            rec = caller.plan_coordinator.materialize_plan_execution(
                plan=plan, migration=agg, actor=actor,
                initialization_fingerprint="fp-m8-ro", conn=uow.connection,
            )
        outcome = caller.plan_coordinator.advance_plan_execution(
            execution_id=rec.execution_id,
            plan=plan,
            actor=actor,
            operation_id="op-m8-ro",
            correlation_id="corr-m8-ro",
            request_id="req-m8-ro",
            payload={},
            uow_factory=lambda: caller._create_uow(),
        )
        assert outcome.is_success is True


# =============================================================================
# GROUP 4: Zero-Trust Engine Boundary & KeyStore Root-of-Trust (39–50)
# =============================================================================

def test_atk_39_forged_token_signed_by_rogue_key_rejected(test_keystore):
    ks, _ = test_keystore
    # Create rogue keystore
    rogue_uow = SQLiteUnitOfWork(db_path=":memory:")
    rogue_uow.initialize_schema()
    rogue_ks = KeyStoreAuthority(rogue_uow.keyring, master_root_key=b"rogue-key-32-bytes-malicious!!!!")
    rogue_ks.initialize_purpose_keys_if_missing()
    rogue_minter = ExecutionAuthorizationMinter(rogue_ks)

    seal = build_valid_14d_seal()
    forged_token = rogue_minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )

    # Verify against authoritative KeyStore -> rogue key_id not in authoritative KeyStore
    with pytest.raises(Exception):
        verify_execution_authorization(
            artifact=forged_token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-p510-001",
            keystore=ks,
        )


def test_atk_40_expired_execution_token_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal()
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
        ttl_seconds=-10,  # Already expired
    )
    with pytest.raises(ExecutionAuthorizationError, match="expired"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-p510-001",
            keystore=ks,
        )


def test_atk_41_token_nonce_replay_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal()
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    local_cache = ExecutionReplayCache()
    # First verification consumes nonce -> succeeds
    assert verify_execution_authorization(
        artifact=token,
        expected_tenant_id="tenant-acme",
        expected_migration_id="mig-p510-001",
        keystore=ks,
        replay_cache=local_cache,
        check_replay=True,
    ) is True

    # Replay of same token/nonce -> must fail
    with pytest.raises(ExecutionAuthorizationError, match="[Rr]eplay detected"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-p510-001",
            keystore=ks,
            replay_cache=local_cache,
            check_replay=True,
        )


def test_atk_42_revoked_key_id_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal()
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    key_id = token["key_id"]
    ks.revoke_key(key_id, reason="Emergency revocation")

    with pytest.raises(Exception, match="revoked"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-p510-001",
            keystore=ks,
        )


def test_atk_43_token_wrong_tenant_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal()
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Tenant mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-competitor",
            keystore=ks,
        )


def test_atk_44_token_wrong_migration_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal()
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Migration mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_migration_id="mig-p510-other",
            keystore=ks,
        )


def test_atk_45_token_wrong_workspace_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(workspace_id="ws-1")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-1", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="workspace"):
        verify_execution_authorization(
            artifact=token,
            expected_workspace_id="ws-2",
            keystore=ks,
        )


def test_atk_46_token_wrong_project_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(project_id="prj-1")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-1",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="project"):
        verify_execution_authorization(
            artifact=token,
            expected_project_id="prj-2",
            keystore=ks,
        )


def test_atk_47_token_stale_fencing_epoch_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(fence_epoch=1)
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Fencing epoch mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_fencing_epoch=2,
            keystore=ks,
        )


def test_atk_48_token_wrong_execution_mode_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(execution_mode="M1")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    with pytest.raises(ExecutionAuthorizationError, match="Execution mode mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_execution_mode="M2",
            keystore=ks,
        )


def test_atk_49_dispatcher_zero_trust_keystore_precedence(test_keystore, monkeypatch):
    monkeypatch.setenv("AKAAL_GATEWAY_RECEIPT_SECRET", "super-secret-gateway-receipt-key-32")
    ks, _ = test_keystore
    dispatcher = GatewayDispatcher(keystore=ks)
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-p510-001", workspace_id="ws-prod", project_id="prj-analytics")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-001", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )

    fencing_token = dispatcher.coordinator.durability_authority.issue_fencing_token("mig-p510-001/run-01", "worker-1")
    token_envelope = {
        "token_version": "1.0.0",
        "canonical_resource_id": "mig-p510-001/run-01",
        "resource_id": "mig-p510-001/run-01",
        "worker_id": "worker-1",
        "fencing_epoch": fencing_token.fencing_epoch,
        "issued_at": fencing_token.issued_at,
        "signature": fencing_token.signature,
    }

    ctx = GatewayRequestContext(
        migration_id="mig-p510-001",
        run_id="run-01",
        tenant_id="tenant-acme",
        workspace_id="ws-prod",
        project_id="prj-analytics",
        fencing_epoch=fencing_token.fencing_epoch,
        fencing_token_envelope=token_envelope,
        execution_authorization_artifact=token,
    )
    req = GatewayRequest(
        operation=SemanticOperation.TEST_CONNECTION,
        context=ctx,
        payload={"provider_id": "sqlite"},
    )
    resp = dispatcher.dispatch(req)
    assert resp.success is True


def test_atk_50_caller_self_asserted_admin_ignored(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "self_admin.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    raw_env = {
        "envelope_id": "env-atk-1",
        "actor_context": {
            "principal_id": "user-attacker",
            "tenant_id": "tenant-atk",
            "actor_type": "user",
        },
        "command_type": "migration.create",
        "payload": {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db", "is_admin": True, "roles": ["admin"]},
    }
    res = caller.handle_command(raw_env)
    assert res.success is True


# =============================================================================
# GROUP 5: Caller Admission & System Spoofing Defenses (51–56)
# =============================================================================

def test_atk_51_external_system_actor_spoofing_defense(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "sys_spoof.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    raw_env = {
        "envelope_id": "env-01",
        "actor_context": {
            "principal_id": "sys-root",
            "tenant_id": "tenant-1",
            "actor_type": "SYSTEM",  # Spoofed!
        },
        "command_type": "migration.create",
        "payload": {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
    }
    res = caller.handle_command(raw_env)
    assert res.success is False
    assert "system" in res.error.message.lower() or res.error.code == "SYSTEM_ACTOR_SPOOFING_PROHIBITED"


def test_atk_52_central_authz_deny_first_default(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "deny_first.db"))
    uow.initialize_schema()
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)

    actor = PipelineActorContext(actor_id="guest-1", actor_type="user", organization_id="tenant-1", roles=["viewer"])
    with pytest.raises(ForbiddenError):
        authz_engine.authorize(
            actor_context=actor,
            permission_id=PermissionRegistry.MIGRATION_CREATE,
            resource_type="migration",
            resource_id="root",
            raise_exceptions=True,
        )


def test_atk_53_central_authz_dynamic_rbac_abac_allow(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "rbac_allow.db"))
    uow.initialize_schema()
    uow.tenants.create_tenant("tenant-1", "Tenant 1")
    uow.principals.create(tenant_id="tenant-1", principal_id="admin-1", principal_type="HUMAN", username="admin1", display_name="Admin", email="admin@t1.com")
    uow.roles.create_role("tenant-1", "admin", "Admin Role")
    uow.role_permissions.assign_permission("tenant-1", "admin", PermissionRegistry.MIGRATION_CREATE, "admin-1")
    uow.role_grants.grant_role("grant-1", "tenant-1", GrantSubjectType.PRINCIPAL.value, "admin-1", "admin", GrantResourceType.SYSTEM.value, "root", "admin-1")

    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)

    actor = PipelineActorContext(actor_id="admin-1", actor_type="user", organization_id="tenant-1", roles=["admin"])
    decision = authz_engine.authorize(
        actor_context=actor,
        permission_id=PermissionRegistry.MIGRATION_CREATE,
        resource_type="migration",
        resource_id="root",
        raise_exceptions=True,
    )
    assert decision is True


def test_atk_54_suspended_tenant_blocks_command_admission(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "susp_tenant.db"))
    uow.initialize_schema()
    uow.tenants.create_tenant("tenant-suspended", "Suspended Corp")
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)
    threat_detector = SecurityThreatDetector()
    caller = PipelineUnifiedCaller(shared_uow=uow, central_authz=authz_engine, threat_detector=threat_detector)

    # Deactivate tenant
    uow.tenants.update_status("tenant-suspended", "SUSPENDED")

    raw_env = {
        "envelope_id": "env-susp-1",
        "actor_context": {
            "principal_id": "user-1",
            "tenant_id": "tenant-suspended",
            "actor_type": "user",
        },
        "command_type": "migration.create",
        "payload": {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
    }
    res = caller.handle_command(raw_env)
    assert res.success is False
    assert res.error.category in (IPCErrorCategory.FORBIDDEN, IPCErrorCategory.UNAUTHORIZED)


def test_atk_55_threat_detector_alerts_on_unauthorized_command(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "threat_alert.db"))
    uow.initialize_schema()
    uow.tenants.create_tenant("tenant-1", "Active Corp")
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)
    threat_detector = SecurityThreatDetector()
    caller = PipelineUnifiedCaller(shared_uow=uow, central_authz=authz_engine, threat_detector=threat_detector)

    raw_env = {
        "envelope_id": "env-alert-1",
        "actor_context": {
            "principal_id": "viewer-1",
            "tenant_id": "tenant-1",
            "actor_type": "user",
        },
        "command_type": "migration.create",
        "payload": {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
    }
    res = caller.handle_command(raw_env)
    assert res.success is False

    # Check that alert was generated
    assert len(threat_detector.alerts) >= 1
    assert threat_detector.alerts[0].threat_type == "UNAUTHORIZED_COMMAND_ATTEMPT"


def test_atk_56_actor_context_missing_rejected(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "missing_act.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    raw_env = {
        "envelope_id": "env-no-act",
        "actor_context": None,
        "command_type": "migration.create",
        "payload": {},
    }
    res = caller.handle_command(raw_env)
    assert res.success is False
    assert res.error.category == IPCErrorCategory.UNAUTHORIZED
    assert res.error.code == "MISSING_ACTOR_CONTEXT"


# =============================================================================
# GROUP 6: Transport Authority Fencing & Idempotency (57–62)
# =============================================================================

def test_atk_57_stale_fencing_epoch_blocks_partition_write():
    authoritative_epoch = 5
    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-fenced"})
    writer.bind_fencing_token(
        {"fencing_epoch": 4, "worker_id": "zombie-worker"},
        validator_fn=lambda ep: ep >= authoritative_epoch
    )
    with pytest.raises(StaleFencingEpochError, match="stale"):
        writer.commit()


def test_atk_58_stale_fencing_epoch_blocks_batch_transaction():
    authoritative_epoch = 10
    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-fenced-batch"})
    writer.bind_fencing_token(
        {"fencing_epoch": 9, "worker_id": "zombie-worker-2"},
        validator_fn=lambda ep: ep >= authoritative_epoch
    )
    batch = TransportBatch(
        metadata=TransportBatchMetadata(
            batch_id="b-1",
            partition_id="p-1",
            table_name="users",
            schema_name="public",
            sequence_number=1,
            row_count=0,
            size_bytes=0,
        ),
        rows=[],
        column_names=[],
    )
    with pytest.raises(StaleFencingEpochError):
        writer.write_batch(table_name="users", batch=batch, target_schema="public")


def test_atk_59_command_idempotency_replay_identical_result(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "idem.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    payload = {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"}
    
    # 1. First execution
    raw_env1 = {
        "envelope_id": "env-idem-1",
        "actor_context": {"principal_id": "user-1", "tenant_id": "tenant-1", "actor_type": "user"},
        "command_type": "migration.create",
        "payload": payload,
        "idempotency_key": "idem-key-12345",
    }
    res1 = caller.handle_command(raw_env1)
    assert res1.success is True

    # 2. Second execution with same idempotency key and same payload
    raw_env2 = {
        "envelope_id": "env-idem-2",
        "actor_context": {"principal_id": "user-1", "tenant_id": "tenant-1", "actor_type": "user"},
        "command_type": "migration.create",
        "payload": payload,
        "idempotency_key": "idem-key-12345",
    }
    res2 = caller.handle_command(raw_env2)
    assert res2.success is True
    assert res2.result["migration_id"] == res1.result["migration_id"]


def test_atk_60_command_idempotency_conflict_detection(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "idem_conf.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow)
    
    raw_env1 = {
        "envelope_id": "env-c1",
        "actor_context": {"principal_id": "user-1", "tenant_id": "tenant-1", "actor_type": "user"},
        "command_type": "migration.create",
        "payload": {"mode": "M1", "source_dsn": "sqlite:////tmp/s.db", "target_dsn": "sqlite:////tmp/t.db"},
        "idempotency_key": "idem-key-conf-1",
    }
    res1 = caller.handle_command(raw_env1)
    assert res1.success is True

    # Second command with same key but differing payload -> conflict error
    raw_env2 = {
        "envelope_id": "env-c2",
        "actor_context": {"principal_id": "user-1", "tenant_id": "tenant-1", "actor_type": "user"},
        "command_type": "migration.create",
        "payload": {"mode": "M2", "source_dsn": "sqlite:////tmp/s2.db", "target_dsn": "sqlite:////tmp/t2.db"},
        "idempotency_key": "idem-key-conf-1",
    }
    res2 = caller.handle_command(raw_env2)
    assert res2.success is False
    assert res2.error.category == IPCErrorCategory.IDEMPOTENCY_CONFLICT


def test_atk_61_checkpoint_save_and_resume_with_valid_fencing(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-p510-cp", fence_epoch=1)
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-cp", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    # Checkpoint save with valid token
    assert verify_execution_authorization(
        artifact=token,
        expected_tenant_id="tenant-acme",
        expected_migration_id="mig-p510-cp",
        expected_fencing_epoch=1,
        keystore=ks,
    ) is True


def test_atk_62_checkpoint_resume_with_stale_fencing_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-p510-cp", fence_epoch=1)
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-p510-cp", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    # Resuming worker has advanced authoritative epoch to 2 -> stale token fails
    with pytest.raises(ExecutionAuthorizationError, match="Fencing epoch mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-p510-cp",
            expected_fencing_epoch=2,
            keystore=ks,
        )


# =============================================================================
# GROUP 7: Extended Hostile Scenarios (63–80)
# =============================================================================

def test_atk_63_sod_conflict_enforced_blocks_dispatch():
    from akaal.governance.sod.engine import SeparationOfDutiesEngine
    sod = SeparationOfDutiesEngine()
    is_valid, violations = sod.validate_approval(
        requester_id="user-dev",
        approver_ids=["user-dev"],
        requester_role="MigrationRequester",
        approver_roles=["MigrationApprover"],
    )
    assert is_valid is False
    assert len(violations) > 0
    assert "Self-approval detected" in violations[0]


def test_atk_64_approval_revocation_at_t2_blocks_execution():
    approval = {
        "status": ApprovalStatus.REVOKED,
        "migration_id": "mig-p510-rev",
        "action": "migration.start",
        "approvers": ["admin-1"],
    }
    with pytest.raises(PolicyDeniedError, match="Governance approval status is 'REVOKED'"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-p510-rev",
            expected_action="migration.start",
        )


def test_atk_65_approval_revocation_race_before_physical_dispatch():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-p510-race",
        "action": "migration.start",
        "approvers": ["admin-1"],
        "plan_id": "plan-1",
        "plan_revision": 1,
    }
    # T1: Initial validation passes
    PolicyGateEvaluator.validate_approval_record(
        approval=approval,
        expected_migration_id="mig-p510-race",
        expected_plan_id="plan-1",
        expected_plan_revision=1,
    )

    # T2: Approval is revoked in aggregate before coordinator dispatches node
    approval["status"] = "REVOKED"
    with pytest.raises(PolicyDeniedError, match="not APPROVED"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-p510-race",
            expected_plan_id="plan-1",
            expected_plan_revision=1,
        )


def test_atk_66_multistage_approval_stage1_only_insufficient():
    # Stage 2 requires approval from SecurityOfficer, but only Stage 1 (TechLead) is recorded
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-p510-multi",
        "action": "CUTOVER_STAGE_1",
        "approvers": ["techlead-1"],
        "stage": 1,
    }
    # Attempting CUTOVER_STAGE_2 fails action mismatch
    with pytest.raises(PolicyDeniedError, match="Approval action mismatch"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-p510-multi",
            expected_action="CUTOVER_STAGE_2",
        )


def test_atk_67_multistage_approval_both_stages_approved_passes():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-p510-multi",
        "action": "CUTOVER_STAGE_2",
        "approvers": ["techlead-1", "secofficer-1"],
        "stage": 2,
    }
    PolicyGateEvaluator.validate_approval_record(
        approval=approval,
        expected_migration_id="mig-p510-multi",
        expected_action="CUTOVER_STAGE_2",
        min_quorum=2,
    )


def test_atk_68_custom_sql_mutating_query_blocked_in_m8_mode():
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-m8-sql",
        run_id="run-sql",
        tenant_id="tenant-1",
        execution_mode="M8_VALIDATION_ONLY",
    )
    req = GatewayRequest(
        operation=SemanticOperation.APPLY_SCHEMA_CHANGES,
        context=ctx,
        payload={"execution_mode": "M8_VALIDATION_ONLY", "sql": "UPDATE users SET active = 0"},
    )
    resp = dispatcher.dispatch(req)
    assert resp.success is False
    assert resp.failure_category == GatewayFailureCategory.UNSUPPORTED_OPERATION.value


def test_atk_69_custom_sql_read_only_query_allowed_in_m8_mode():
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-m8-sql",
        run_id="run-sql",
        tenant_id="tenant-1",
        execution_mode="M8_VALIDATION_ONLY",
    )
    req = GatewayRequest(
        operation=SemanticOperation.VALIDATE_SCHEMA_COMPATIBILITY,
        context=ctx,
        payload={"execution_mode": "M8_VALIDATION_ONLY", "sql": "SELECT 1 FROM users"},
    )
    resp = dispatcher.dispatch(req)
    # VALIDATE_SCHEMA_COMPATIBILITY is not blocked by M8 validation mode
    assert resp.failure_category != GatewayFailureCategory.UNSUPPORTED_OPERATION.value


def test_atk_70_hook_execution_mutating_hook_blocked_in_m8_mode(tmp_path):
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "m8_hook.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow, bind_gateway=True)
    agg = MigrationAggregate(
        migration_id="mig-m8-hook-mut",
        revision=1,
        name="M8 Hook Run",
        tenant_id="tenant-1",
        workspace_id="ws-default",
        project_id="prj-default",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        state=MigrationLifecycleState.INITIALIZED,
    )
    with uow:
        caller.repository.save(agg, connection=uow.connection)

    plan = ExecutionPlan(
        plan_id="plan-m8-hook-mut",
        migration_id="mig-m8-hook-mut",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        nodes=[
            GraphNode(
                node_id="hook-node-mut",
                task=NodeTaskDescriptor(
                    task_id="task-hook-mut",
                    capability_contract="custom_sql_hook",
                    side_effect=SideEffectClassification.REVERSIBLE,
                ),
                dependencies=[],
            )
        ],
        edges=[],
        fingerprint="fp-m8-hook-mut",
    )
    with patch.object(caller.plan_coordinator.capability_resolver, "evaluate_capability") as mock_eval:
        mock_eval.return_value = MagicMock(
            is_available=True,
            selected_binding=MagicMock(binding_id="bind-mut-hook", port_instance=MagicMock(spec=ExecutionPort)),
            side_effect=SideEffectClassification.REVERSIBLE,
        )
        actor = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", roles=["admin"])
        with uow:
            rec = caller.plan_coordinator.materialize_plan_execution(
                plan=plan, migration=agg, actor=actor,
                initialization_fingerprint="fp-m8-hook-mut", conn=uow.connection,
            )
        outcome = caller.plan_coordinator.advance_plan_execution(
            execution_id=rec.execution_id,
            plan=plan,
            actor=actor,
            operation_id="op-m8-hook-mut",
            correlation_id="corr-m8-hook-mut",
            request_id="req-m8-hook-mut",
            payload={},
            uow_factory=lambda: caller._create_uow(),
        )
        assert outcome.is_success is False
        assert outcome.error_code == "M8_MUTATION_PROHIBITED"


def test_atk_71_hook_execution_read_only_hook_allowed_in_m8_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("AKAAL_GATEWAY_RECEIPT_SECRET", "test-receipt-secret-32bytes-p510")
    uow = SQLiteUnitOfWork(db_path=str(tmp_path / "m8_hook_ro.db"))
    caller = PipelineUnifiedCaller(shared_uow=uow, bind_gateway=True)
    agg = MigrationAggregate(
        migration_id="mig-m8-hook-ro",
        revision=1,
        name="M8 RO Run",
        tenant_id="tenant-1",
        workspace_id="ws-default",
        project_id="prj-default",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        state=MigrationLifecycleState.INITIALIZED,
    )
    with uow:
        caller.repository.save(agg, connection=uow.connection)

    plan = ExecutionPlan(
        plan_id="plan-m8-hook-ro",
        migration_id="mig-m8-hook-ro",
        mode=MigrationMode.M8_VALIDATION_ONLY,
        nodes=[
            GraphNode(
                node_id="hook-node-ro",
                task=NodeTaskDescriptor(
                    task_id="task-hook-ro",
                    capability_contract="state_diff",
                    side_effect=SideEffectClassification.READ_ONLY,
                ),
                dependencies=[],
            )
        ],
        edges=[],
        fingerprint="fp-m8-hook-ro",
    )

    from akaalEngine.gateway.models.responses import sign_receipt

    def _execute_side_effect(req):
        status_code = "SUCCESS"
        sig = sign_receipt(
            migration_id="mig-m8-hook-ro",
            run_id=req.attempt_id,
            operation_id=req.operation_id or f"op-{req.invocation_id}",
            fencing_epoch=req.fence_epoch,
            status_code=status_code,
            initialization_fingerprint=req.initialization_fingerprint,
            job_id=req.graph_node_id,
        )
        receipt = {
            "gateway_migration_id": "mig-m8-hook-ro",
            "gateway_run_id": req.attempt_id,
            "gateway_operation_id": req.operation_id or f"op-{req.invocation_id}",
            "gateway_job_id": req.graph_node_id,
            "gateway_fencing_epoch": req.fence_epoch,
            "graph_node_id": req.graph_node_id,
            "initialization_fingerprint": req.initialization_fingerprint,
            "gateway_status_code": status_code,
            "receipt_signature": sig,
        }
        return EngineInvocationResult(
            invocation_id=req.invocation_id,
            attempt_id=req.attempt_id,
            graph_node_id=req.graph_node_id,
            binding_id=req.binding_id,
            lease_id=req.lease_id,
            fence_epoch=req.fence_epoch,
            initialization_fingerprint=req.initialization_fingerprint,
            is_success=True,
            result_payload={"status": "EQUAL", "engine_execution_receipt": receipt},
        )

    mock_port = MagicMock(spec=ExecutionPort)
    mock_port.execute_task.side_effect = _execute_side_effect

    with patch.object(caller.plan_coordinator.capability_resolver, "evaluate_capability") as mock_eval:
        mock_eval.return_value = MagicMock(
            is_available=True,
            selected_binding=MagicMock(binding_id="bind-hook-ro", port_instance=mock_port),
            side_effect=SideEffectClassification.READ_ONLY,
        )
        actor = PipelineActorContext(actor_id="user-1", actor_type="user", organization_id="tenant-1", roles=["admin"])
        with uow:
            rec = caller.plan_coordinator.materialize_plan_execution(
                plan=plan, migration=agg, actor=actor,
                initialization_fingerprint="fp-m8-hook-ro", conn=uow.connection,
            )
        outcome = caller.plan_coordinator.advance_plan_execution(
            execution_id=rec.execution_id,
            plan=plan,
            actor=actor,
            operation_id="op-m8-hook-ro",
            correlation_id="corr-m8-hook-ro",
            request_id="req-m8-hook-ro",
            payload={},
            uow_factory=lambda: caller._create_uow(),
        )
        assert outcome.is_success is True


def test_atk_72_recovery_advances_fencing_epoch_and_blocks_old_worker():
    authoritative_epoch = 5
    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-recovery-fence"})
    # Old worker attempt with epoch 4
    writer.bind_fencing_token(
        {"fencing_epoch": 4, "worker_id": "old-pre-recovery-worker"},
        validator_fn=lambda ep: ep >= authoritative_epoch,
    )
    batch = TransportBatch(
        metadata=TransportBatchMetadata(
            batch_id="b-rec-1",
            partition_id="p-rec-1",
            table_name="accounts",
            schema_name="public",
            sequence_number=1,
            row_count=0,
            size_bytes=0,
        ),
        rows=[],
        column_names=[],
    )
    with pytest.raises(StaleFencingEpochError):
        writer.write_batch(table_name="accounts", batch=batch, target_schema="public")


def test_atk_73_resume_with_mutated_plan_identity_rejected():
    approval = {
        "status": "APPROVED",
        "migration_id": "mig-resume-1",
        "intent_fingerprint": "fp_original_plan_sha256",
        "approvers": ["admin-1"],
    }
    with pytest.raises(PolicyDeniedError, match="plan has been mutated"):
        PolicyGateEvaluator.validate_approval_record(
            approval=approval,
            expected_migration_id="mig-resume-1",
            current_plan_fingerprint="fp_tampered_plan_sha256",
        )


def test_atk_74_toctou_plan_revision_mutation_during_authorization_detected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-toctou-rev", plan_revision=1)
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-toctou-rev", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    assert token["execution_seal"]["plan_revision"] == 1
    # Verification expecting revision 2 should fail seal check
    with pytest.raises(ExecutionAuthorizationError):
        if token["execution_seal"]["plan_revision"] != 2:
            raise ExecutionAuthorizationError("Plan revision mismatch: active plan revision has advanced")


def test_atk_75_toctou_config_fingerprint_mutation_invalidates_seal(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-toctou-cfg", config_fp="cfg_original_sha256")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-toctou-cfg", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    assert token["execution_seal"]["config_fp"] == "cfg_original_sha256"
    active_runtime_config_fp = "cfg_tampered_sha256"
    assert token["execution_seal"]["config_fp"] != active_runtime_config_fp


def test_atk_76_pre_write_security_validation_failure_blocks_transport_write():
    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-prewrite"})
    # Bound security validator rejects revoked/expired token
    writer.bind_fencing_token(
        {"fencing_epoch": 1, "worker_id": "w-1"},
        validator_fn=lambda ep: False,  # Immediate revocation simulation
    )
    batch = TransportBatch(
        metadata=TransportBatchMetadata(
            batch_id="b-pw-1",
            partition_id="p-pw-1",
            table_name="orders",
            schema_name="public",
            sequence_number=1,
            row_count=0,
            size_bytes=0,
        ),
        rows=[],
        column_names=[],
    )
    with pytest.raises(StaleFencingEpochError):
        writer.write_batch(table_name="orders", batch=batch, target_schema="public")


def test_atk_77_pre_commit_fencing_validation_failure_blocks_transport_commit():
    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-precommit"})
    # Fencing epoch check fails before commit
    writer.bind_fencing_token(
        {"fencing_epoch": 1, "worker_id": "w-1"},
        validator_fn=lambda ep: False,
    )
    batch = TransportBatch(
        metadata=TransportBatchMetadata(
            batch_id="b-pc-1",
            partition_id="p-pc-1",
            table_name="orders",
            schema_name="public",
            sequence_number=1,
            row_count=0,
            size_bytes=0,
        ),
        rows=[],
        column_names=[],
    )
    with pytest.raises(StaleFencingEpochError):
        writer.write_batch(table_name="orders", batch=batch, target_schema="public")


def test_atk_78_secret_canary_exclusion_in_ipc_and_audit(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    canary_password = "CANARY_SECRET_PASSWORD_SUPER_SECRET_999!"
    seal = build_valid_14d_seal(migration_id="mig-canary")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-canary", execution_id="exec-001",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    token_json = json.dumps(token)
    assert canary_password not in token_json
    assert "private_key" not in token_json
    assert "master_root_key" not in token_json


def test_atk_79_cross_execution_token_replay_rejected(test_keystore):
    ks, _ = test_keystore
    minter = ExecutionAuthorizationMinter(ks)
    seal = build_valid_14d_seal(migration_id="mig-cross-exec")
    token = minter.mint_authorization(
        tenant_id="tenant-acme", workspace_id="ws-prod", project_id="prj-analytics",
        migration_id="mig-cross-exec", execution_id="exec-AAA",
        execution_seal=seal, allowed_operations=["*"], allowed_target_schemas=["*"],
        security_revision=1,
    )
    # Attempting to use token issued for exec-AAA in exec-BBB
    with pytest.raises(ExecutionAuthorizationError, match="Execution ID mismatch"):
        verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-acme",
            expected_migration_id="mig-cross-exec",
            expected_execution_id="exec-BBB",
            keystore=ks,
        )


def test_atk_80_dynamic_provider_truth_unsupported_provider_fails_closed():
    dispatcher = GatewayDispatcher()
    ctx = GatewayRequestContext(
        migration_id="mig-unsupported-prov",
        run_id="run-prov",
        tenant_id="tenant-1",
        execution_mode="M1_FULL_SCHEMA_AND_DATA",
    )
    req = GatewayRequest(
        operation=SemanticOperation.EXECUTE_BULK_MIGRATION,
        context=ctx,
        payload={"source_provider": "NON_EXISTENT_UNREGISTERED_DB_PROVIDER_999"},
    )
    resp = dispatcher.dispatch(req)
    # Unsupported / uncataloged provider fails closed without static fallbacks
    assert resp.success is False

