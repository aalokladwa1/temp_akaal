import time
import threading
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.execution_authorization import ExecutionAuthorizationMinter
from akaalPipeline.security.seal import ExecutionSealBuilder
from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from typing import Any
from dataclasses import dataclass
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from unittest.mock import patch

@dataclass
class DummyRequest:
    context: GatewayRequestContext
    operation: SemanticOperation
    payload: dict

def test_active_worker_fencing_during_execution_loop(tmp_path):
    db_path = str(tmp_path / "fencing1.db")
    uow = SQLiteUnitOfWork(db_path=db_path)
    ks = KeyStoreAuthority(keyring_repo=uow.keyring, master_root_key=b"mrk-32byte-test-key-p59-blocker6")
    ks.initialize_purpose_keys_if_missing()
    minter = ExecutionAuthorizationMinter(ks)

    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-02", plan_id="plan-b6-02", plan_revision=1,
        execution_mode="M1", source_identity_fp="src-fp", target_identity_fp="tgt-fp",
        selection_scope_fp="sel-fp", config_fp="cfg-fp", initialization_fp="init-fp",
        approval_fp="appr-fp", fence_epoch=1,
    )

    token = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-02", execution_id="exec-b6-02",
        execution_seal=seal, allowed_operations=["MUTATE", "MIGRATE"],
        allowed_target_schemas=["public"], security_revision=1,
    )
    key_id = token["key_id"]
    pub_pem = ks.get_public_key_pem(key_id)
    
    if hasattr(uow, 'conn'):
        uow.conn.commit()

    dispatcher = GatewayDispatcher(keystore=ks)

    worker_results = []
    chunk_processed = threading.Event()
    
    def active_worker_loop():
        # Create a thread-local unit of work and keystore connecting to the same DB
        thread_uow = SQLiteUnitOfWork(db_path=db_path)
        thread_ks = KeyStoreAuthority(keyring_repo=thread_uow.keyring, master_root_key=b"mrk-32byte-test-key-p59-blocker6")
        thread_dispatcher = GatewayDispatcher(keystore=thread_ks)
        
        # Simulate worker processing chunks
        with patch('akaalPipeline.security.execution_authorization.ExecutionReplayCache.record_and_verify', return_value=None):
            for chunk in range(5):
                ctx = GatewayRequestContext(
                    tenant_id="tenant-corp",
                    migration_id="mig-b6-02",
                    run_id="run-2",
                    operation_id=f"op-chunk-{chunk}",
                    execution_authorization_artifact=token,
                    fencing_epoch=1
                )
                req = DummyRequest(
                    context=ctx,
                    operation=SemanticOperation.TEST_CONNECTION,
                    payload={"execution_signing_public_key_pem": pub_pem}
                )
                res = thread_dispatcher.dispatch(req)
                worker_results.append((chunk, res.success, res.error_message))
                chunk_processed.set()
                if "Execution authorization verification failed" in str(res.error_message):
                    break
                time.sleep(0.1)

    t = threading.Thread(target=active_worker_loop)
    t.start()
    
    # Wait for worker to complete at least one chunk successfully
    chunk_processed.wait(timeout=2.0)
    
    # Revoke key while worker is actively running
    ks.revoke_key(key_id, "Revoked by control plane during partition")
    if hasattr(uow, 'conn'):
        uow.conn.commit()
    
    t.join(timeout=2.0)
    
    # Ensure worker processed some chunks successfully, but failed after revocation
    assert len(worker_results) > 1
    assert len(worker_results) < 5
    
    last_result = worker_results[-1]
    assert last_result[1] is False
    assert "Execution authorization verification failed" in str(last_result[2])
    assert "Signature verification blocked on revoked key" in str(last_result[2])


def test_distributed_network_partition_fencing(tmp_path):
    # Similar proof but simulates remote node with partitioned keystore
    db_path = str(tmp_path / "fencing2.db")
    uow_central = SQLiteUnitOfWork(db_path=db_path)
    ks_central = KeyStoreAuthority(keyring_repo=uow_central.keyring, master_root_key=b"mrk-32byte-test-key-p59-blocker6")
    ks_central.initialize_purpose_keys_if_missing()
    minter = ExecutionAuthorizationMinter(ks_central)
    
    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-03", plan_id="plan-b6-03", plan_revision=1,
        execution_mode="M1", source_identity_fp="src-fp", target_identity_fp="tgt-fp",
        selection_scope_fp="sel-fp", config_fp="cfg-fp", initialization_fp="init-fp",
        approval_fp="appr-fp", fence_epoch=1,
    )
    token = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-03", execution_id="exec-b6-03",
        execution_seal=seal, allowed_operations=["MUTATE", "MIGRATE"],
        allowed_target_schemas=["public"], security_revision=1,
    )
    key_id = token["key_id"]
    pub_pem = ks_central.get_public_key_pem(key_id)
    
    # Remote node shares the central keystore (or a replicated replica)
    dispatcher_remote = GatewayDispatcher(keystore=ks_central)
    
    ctx = GatewayRequestContext(
        tenant_id="tenant-corp",
        migration_id="mig-b6-03",
        run_id="run-3",
        operation_id="op-chunk-1",
        execution_authorization_artifact=token,
        fencing_epoch=1
    )
    req = DummyRequest(
        context=ctx,
        operation=SemanticOperation.TEST_CONNECTION,
        payload={"execution_signing_public_key_pem": pub_pem}
    )
    
    res1 = dispatcher_remote.dispatch(req)
    assert "Execution authorization verification failed" not in str(res1.error_message)
    
    # Network partition or central node revokes the key
    ks_central.revoke_key(key_id, "Revoked by central control plane")
    
    ctx2 = GatewayRequestContext(
        tenant_id="tenant-corp",
        migration_id="mig-b6-03",
        run_id="run-3",
        operation_id="op-chunk-2",
        execution_authorization_artifact=token,
        fencing_epoch=1
    )
    req2 = DummyRequest(
        context=ctx2,
        operation=SemanticOperation.TEST_CONNECTION,
        payload={"execution_signing_public_key_pem": pub_pem}
    )
    
    # Remote node immediately fails on next attempt because signature is now locally invalid
    res2 = dispatcher_remote.dispatch(req2)
    assert res2.success is False
    assert "Execution authorization verification failed" in str(res2.error_message)
    assert "Signature verification blocked on revoked key" in str(res2.error_message)
