"""tests.security.test_p59_blocker6_active_revocation
======================================================
BLOCKER 6: Active Execution Revocation Proof.
Proves that a revoked key prevents the next mandatory Engine mutation
path (GatewayDispatcher barrier) from executing, fencing an active worker.
"""
import pytest
from akaalPipeline.security.keystore import KeyStoreAuthority, KeyRevokedError
from akaalPipeline.security.execution_authorization import ExecutionAuthorizationMinter, ExecutionReplayCache
from akaalPipeline.security.seal import ExecutionSealBuilder
from akaalPipeline.contracts.enums import KeyPurpose
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

from akaalEngine.gateway.routing.dispatcher import GatewayDispatcher
from akaalEngine.gateway.orchestration.coordinator import GatewayCoordinator
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import SemanticOperation
from akaalEngine.gateway.models.requests import GatewayRequest

class DummyRequest:
    def __init__(self, context, operation, payload=None):
        self.context = context
        self.operation = operation
        self.payload = payload or {}

def test_active_execution_revocation_at_engine_barrier():
    uow = SQLiteUnitOfWork(db_path=":memory:")
    ks = KeyStoreAuthority(keyring_repo=uow.keyring, master_root_key=b"mrk-32byte-test-key-p59-blocker6")
    ks.initialize_purpose_keys_if_missing()
    minter = ExecutionAuthorizationMinter(ks)

    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-01", plan_id="plan-b6-01", plan_revision=1,
        execution_mode="M1", source_identity_fp="src-fp", target_identity_fp="tgt-fp",
        selection_scope_fp="sel-fp", config_fp="cfg-fp", initialization_fp="init-fp",
        approval_fp="appr-fp", fence_epoch=1,
    )
    # Mint two tokens beforehand to avoid Replay Error and avoid Minter failing post-revocation
    token1 = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-01", execution_id="exec-b6-01",
        execution_seal=seal, allowed_operations=["MUTATE", "MIGRATE"],
        allowed_target_schemas=["public"], security_revision=1,
    )
    token2 = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-01", execution_id="exec-b6-01",
        execution_seal=seal, allowed_operations=["MUTATE", "MIGRATE"],
        allowed_target_schemas=["public"], security_revision=1,
    )
    key_id = token1["key_id"]
    pub_pem = ks.get_public_key_pem(key_id)

    # Engine Gateway initialized with independent access to KeyStore
    dispatcher = GatewayDispatcher(keystore=ks)

    ctx = GatewayRequestContext(
        tenant_id="tenant-corp",
        migration_id="mig-b6-01",
        run_id="run-1",
        operation_id="op-1",
        execution_authorization_artifact=token1,
        fencing_epoch=1
    )
    req1 = DummyRequest(
        context=ctx, 
        operation=SemanticOperation.TEST_CONNECTION,
        payload={"execution_signing_public_key_pem": pub_pem}
    )
    
    # 1. First execution (pre-revocation) succeeds authorization check
    res1 = dispatcher.dispatch(req1)
    # The dispatcher should pass authorization and then maybe fail at actual connection (no payload provided),
    # but it MUST NOT return INVALID_REQUEST due to auth failure.
    assert "Execution authorization verification failed" not in getattr(res1, "error_message", "")

    # 2. Key is revoked during active execution
    ks.revoke_key(key_id, "Revoked mid-execution")

    ctx2 = GatewayRequestContext(
        tenant_id="tenant-corp",
        migration_id="mig-b6-01",
        run_id="run-1",
        operation_id="op-2",
        execution_authorization_artifact=token2,
        fencing_epoch=1
    )
    req2 = DummyRequest(
        context=ctx2, 
        operation=SemanticOperation.EXECUTE_BULK_MIGRATION,
        payload={"execution_signing_public_key_pem": pub_pem}
    )
    
    res2 = dispatcher.dispatch(req2)
    assert res2.success is False
    assert "Execution authorization verification failed" in str(res2.error_message)
    assert "Signature verification blocked on revoked key" in str(res2.error_message)


def test_same_running_worker_revocation_at_physical_batch_barrier():
    """
    CRITICAL DOMAIN 29 PROOF:
    Proves that the SAME actively executing worker revalidates security state at the physical
    batch/commit barrier and halts immediately when the signing key / JIT privilege is revoked
    mid-execution, preventing any subsequent unauthorized mutation or checkpoint advance.
    """
    import sqlite3
    import tempfile
    import os
    from akaalEngine.transport.api import TransportAuthority
    from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
    from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
    from akaalEngine.transport.models.spec import TransportPartition, PartitionStrategy
    from akaalEngine.transport.models.errors import TransportFencingError
    from akaalEngine.durability.api import DurabilityAuthority
    from akaalEngine.durability.models import DurabilityConfig
    from akaalPipeline.security.execution_authorization import verify_execution_authorization

    uow = SQLiteUnitOfWork(db_path=":memory:")
    ks = KeyStoreAuthority(keyring_repo=uow.keyring, master_root_key=b"mrk-32byte-test-key-p59-blocker6")
    ks.initialize_purpose_keys_if_missing()
    minter = ExecutionAuthorizationMinter(ks)

    seal = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-worker", plan_id="plan-b6-01", plan_revision=1,
        execution_mode="M1", source_identity_fp="src-fp", target_identity_fp="tgt-fp",
        selection_scope_fp="sel-fp", config_fp="cfg-fp", initialization_fp="init-fp",
        approval_fp="appr-fp", fence_epoch=1,
    )
    token = minter.mint_authorization(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-b6-worker", execution_id="exec-b6-worker",
        execution_seal=seal, allowed_operations=["MUTATE", "MIGRATE"],
        allowed_target_schemas=["public"], security_revision=1,
    )
    key_id = token["key_id"]

    dur_dir = tempfile.mkdtemp(prefix="dur_active_rev_")
    dur_auth = DurabilityAuthority(config=DurabilityConfig(
        storage_dir=dur_dir,
        fencing_signing_key=b"f" * 32,
        journal_anchor_key=b"j" * 32,
    ))
    f_token = dur_auth.issue_fencing_token("mig-b6-worker", "worker-01")

    transport = TransportAuthority(durability_authority=dur_auth)

    # Multi-batch source simulator
    class MultiBatchSourceReader(SourceReader):
        def __init__(self):
            self.current_seq = 0
            self.is_open = False
            self.batches = [
                [{"id": 1, "val": "batch1_row1"}, {"id": 2, "val": "batch1_row2"}],
                [{"id": 3, "val": "batch2_row1"}, {"id": 4, "val": "batch2_row2"}],
                [{"id": 5, "val": "batch3_row1"}, {"id": 6, "val": "batch3_row2"}],
            ]

        def get_capabilities(self):
            from akaalEngine.transport.models.capabilities import ProviderCapabilities, IdempotencyMode, LOBMode, ResumabilityMode, CommitOutcomeState
            return ProviderCapabilities(
                bulk_read=True,
                bulk_write=True,
                idempotency=IdempotencyMode.OPERATION_IDEMPOTENT,
                resumability=ResumabilityMode.EXACT_RESUME,
            )

        def open_partition(self, partition, last_committed_key=None):
            self.is_open = True

        def read_batch(self, batch_size=1000):
            if self.current_seq >= len(self.batches):
                return None
            rows = self.batches[self.current_seq]
            self.current_seq += 1
            meta = TransportBatchMetadata(
                batch_id=f"batch-{self.current_seq}",
                partition_id="part-01",
                table_name="customer_data",
                schema_name="public",
                sequence_number=self.current_seq,
                row_count=len(rows),
                size_bytes=len(rows) * 32,
            )
            return TransportBatch(metadata=meta, rows=rows, column_names=["id", "val"])

        def cancel(self):
            pass

        def close(self):
            self.is_open = False

        def get_position(self):
            return None

    # Target writer recording committed rows
    class AuditedTargetWriter(TargetWriter):
        def __init__(self):
            super().__init__()
            self.committed_rows = []
            self.uncommitted_rows = []
            self._in_transaction = False

        def bind_identity(self, migration_id, batch_id, endpoint_identity=None):
            super().bind_identity(migration_id, batch_id, endpoint_identity)

        def write_batch(self, table_name, batch, target_schema="public", pk_columns=None, allow_merge=True):
            self._in_transaction = True
            self.uncommitted_rows.extend(batch.rows)
            return len(batch.rows)

        def verify_uncertain_commit(self, table_name, target_schema, pk_columns, batch):
            from akaalEngine.transport.models.capabilities import CommitOutcomeState
            return CommitOutcomeState.COMMITTED

        def commit(self):
            self.committed_rows.extend(self.uncommitted_rows)
            self.uncommitted_rows.clear()
            self._in_transaction = False

        def rollback(self):
            self.uncommitted_rows.clear()
            self._in_transaction = False

        def cancel(self):
            pass

        def close(self):
            pass

        def get_capabilities(self):
            from akaalEngine.transport.models.capabilities import ProviderCapabilities, IdempotencyMode, LOBMode, ResumabilityMode, CommitOutcomeState
            return ProviderCapabilities(
                bulk_read=True,
                bulk_write=True,
                idempotency=IdempotencyMode.OPERATION_IDEMPOTENT,
                resumability=ResumabilityMode.EXACT_RESUME,
            )

    reader = MultiBatchSourceReader()
    writer = AuditedTargetWriter()

    partition = TransportPartition(
        partition_id="part-01",
        table_name="customer_data",
        schema_name="public",
        target_schema="public",
        strategy=PartitionStrategy.PK_NUMERIC_RANGE,
    )

    call_count = 0
    def dynamic_security_barrier():
        nonlocal call_count
        call_count += 1
        # Trigger revocation in authoritative SQLite Keyring after Batch 1 has been read/written/committed
        if call_count >= 5:
            ks.revoke_key(key_id, "Mid-execution security revocation")

        # Canonical execution authorization verification against authoritative durable KeyStore
        return verify_execution_authorization(
            artifact=token,
            expected_tenant_id="tenant-corp",
            expected_migration_id="mig-b6-worker",
            keystore=ks,
            check_replay=False,
        )

    # Execute active worker partition transport
    with pytest.raises(TransportFencingError) as exc_info:
        transport.execute_partition_transport(
            reader=reader,
            writer=writer,
            partition=partition,
            fencing_token=f_token,
            migration_id="mig-b6-worker",
            security_revalidator=dynamic_security_barrier,
        )

    assert "Signature verification blocked on revoked key" in str(exc_info.value) or "Execution authorization revoked" in str(exc_info.value)

    # Prove Batch 1 was committed before revocation
    assert len(writer.committed_rows) == 2
    assert writer.committed_rows[0]["id"] == 1
    assert writer.committed_rows[1]["id"] == 2

    # Prove subsequent batches (Batch 2 and Batch 3) were NEVER committed
    assert len(writer.uncommitted_rows) == 0
    assert not any(r["id"] in (3, 4, 5, 6) for r in writer.committed_rows)

    # Prove durable checkpoint did NOT advance past batch-1
    latest_chk = dur_auth.get_latest_checkpoint("mig-b6-worker")
    assert latest_chk is not None
    assert latest_chk.job_id == "batch-1"

