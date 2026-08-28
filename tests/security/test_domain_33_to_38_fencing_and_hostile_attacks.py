"""tests.security.test_domain_33_to_38_fencing_and_hostile_attacks
================================================================
Hostile security tests for Physical Mutation Fencing, Zero-Trust Engine Gateway, System Spoofing Defense, and Enterprise Bootstrap (Domains 33-38).
"""

import os
import pytest
from akaalEngine.gateway.api import EngineGateway
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory, SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest
from akaalEngine.transport.drivers.base import StaleFencingEpochError
from akaalEngine.transport.drivers.generic_sql import GenericSQLTargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalIPC.protocol.envelopes import CommandEnvelope
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.errors import ConflictError
from akaalPipeline.security.bootstrap import EnterpriseBootstrapCoordinator
from akaalPipeline.security.execution_authorization import ExecutionAuthorizationMinter
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.seal import ExecutionSealBuilder
from akaalPipeline.state.repositories import SQLiteKeyringRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


def test_enterprise_bootstrap_exactly_once():
    uow = SQLiteUnitOfWork(db_path=":memory:")
    mrk = b"\x04" * 32
    coordinator = EnterpriseBootstrapCoordinator(uow, master_root_key=mrk)

    # 1. First bootstrap succeeds
    assert coordinator.is_bootstrapped() is False
    res = coordinator.bootstrap(
        initial_tenant_id="tenant-corp",
        initial_tenant_name="Enterprise Corp",
        admin_username="global-admin",
        admin_password="SuperAdminSecret123!",
        admin_email="admin@enterprise.com",
    )
    assert res["status"] == "BOOTSTRAP_COMPLETED"
    assert coordinator.is_bootstrapped() is True

    # 2. Second bootstrap attempt fails closed with ConflictError
    with pytest.raises(ConflictError, match="already bootstrapped"):
        coordinator.bootstrap(
            initial_tenant_id="tenant-attacker",
            initial_tenant_name="Attacker Corp",
            admin_username="attacker-admin",
            admin_password="Password123!",
        )


def test_physical_mutation_fencing_stale_worker_rollback():
    authoritative_epoch = 2

    def validator(epoch: int) -> bool:
        return epoch >= authoritative_epoch

    writer = GenericSQLTargetWriter(connection_params={"migration_id": "mig-fenced-1"})
    # Stale worker has epoch 1
    writer.bind_fencing_token({"fencing_epoch": 1, "worker_id": "zombie-worker"}, validator_fn=validator)

    # Physical mutation check raises StaleFencingEpochError
    with pytest.raises(StaleFencingEpochError, match="worker epoch 1 is stale"):
        writer.commit()


def test_gateway_zero_trust_execution_authorization_verification(monkeypatch):
    monkeypatch.setenv("AKAAL_GATEWAY_RECEIPT_SECRET", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")

    uow = SQLiteUnitOfWork(db_path=":memory:")
    keyring_repo = SQLiteKeyringRepository(uow.connection)
    keystore = KeyStoreAuthority(keyring_repo, master_root_key=b"\x05" * 32)
    keystore.initialize_purpose_keys_if_missing()
    minter = ExecutionAuthorizationMinter(keystore)

    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_mode="M1",
        source_identity_fp="src-1",
        target_identity_fp="tgt-1",
        selection_scope_fp="scope-1",
        config_fp="cfg-1",
        initialization_fp="init-1",
        approval_fp="appr-1",
        fence_epoch=1,
    )

    artifact = minter.mint_authorization(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        project_id="prj-1",
        migration_id="mig-1",
        execution_id="exec-1",
        execution_seal=seal,
        allowed_operations=["data_transport"],
        allowed_target_schemas=["public"],
        security_revision=1,
    )
    pub_pem = keystore.get_public_key_pem(artifact["key_id"])

    gw = EngineGateway()
    fencing_token = gw.coordinator.durability_authority.issue_fencing_token("mig-1/run-1", "worker-1")
    token_envelope = {
        "token_version": "1.0.0",
        "canonical_resource_id": "mig-1/run-1",
        "resource_id": "mig-1/run-1",
        "worker_id": "worker-1",
        "fencing_epoch": fencing_token.fencing_epoch,
        "issued_at": fencing_token.issued_at,
        "signature": fencing_token.signature,
    }

    # 1. Dispatching with valid authorization and fencing token
    ctx_valid = GatewayRequestContext(
        migration_id="mig-1",
        run_id="run-1",
        tenant_id="tenant-1",
        fencing_epoch=fencing_token.fencing_epoch,
        fencing_token_envelope=token_envelope,
        execution_authorization_artifact=artifact,
    )
    req_valid = GatewayRequest(
        operation=SemanticOperation.RESOLVE_CAPABILITIES,
        context=ctx_valid,
        payload={"provider_id": "sqlite", "required_capabilities": [], "execution_signing_public_key_pem": pub_pem},
    )
    resp_valid = gw.execute(req_valid)
    assert resp_valid.success is True

    # 2. Dispatching with tampered authorization fails closed at Gateway
    tampered_artifact = dict(artifact)
    tampered_artifact["tenant_id"] = "foreign-tenant"
    ctx_tampered = GatewayRequestContext(
        migration_id="mig-1",
        run_id="run-1",
        tenant_id="tenant-1",
        fencing_epoch=fencing_token.fencing_epoch,
        fencing_token_envelope=token_envelope,
        execution_authorization_artifact=tampered_artifact,
    )
    req_tampered = GatewayRequest(
        operation=SemanticOperation.RESOLVE_CAPABILITIES,
        context=ctx_tampered,
        payload={"provider_id": "sqlite", "required_capabilities": [], "execution_signing_public_key_pem": pub_pem},
    )
    resp_tampered = gw.execute(req_tampered)
    assert resp_tampered.success is False
    assert "Execution authorization verification failed" in resp_tampered.error_message


def test_system_actor_identity_spoofing_defense():
    caller = PipelineUnifiedCaller(db_path=":memory:")

    # External actor trying to manufacture "system" actor identity
    spoofed_actor = ActorContext(
        actor=ActorReference(actor_id="hacker", actor_type="SYSTEM"),
        organization_id="tenant-1",
        provenance="untrusted-external-network",
    )

    cmd = CommandEnvelope(
        request_id="req-spoof-1",
        protocol_version="1.0.0",
        schema_version="1.0.0",
        request_type="migration.create",
        kind=RequestKind.COMMAND,
        actor=spoofed_actor,
        correlation=CorrelationContext.new(),
        payload={"migration_id": "mig-spoof-1"},
        command_id="cmd-spoof-1",
    )

    res = caller.handle_command(cmd)
    # Must be rejected with UNAUTHORIZED category
    assert res.status == CallerResultStatus.ERROR
    assert res.error.category == IPCErrorCategory.UNAUTHORIZED
    assert "SYSTEM_ACTOR_SPOOFING_PROHIBITED" in res.error.code
