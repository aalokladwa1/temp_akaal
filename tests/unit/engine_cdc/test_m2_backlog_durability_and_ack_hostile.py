"""
tests/unit/engine_cdc/test_m2_backlog_durability_and_ack_hostile.py
==================================================================
Hostile proof of CDC Backlog Buffer crash/restart durability and ACK safety.
Proves that pending backlog events survive process/coordinator destruction,
reconstruct with 100% fidelity from Authority #5 Durability, and never lose or corrupt ordering.
"""

import os
import shutil
import tempfile
import pytest
from typing import Dict, Any

from akaalEngine.cdc.buffering.backlog import CDCBacklogBuffer
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType, TransactionContext
from akaalEngine.durability.api import DurabilityAuthority
from akaalEngine.durability.models import DurabilityConfig, MigrationCheckpoint, FencingToken


@pytest.fixture
def durability_env():
    temp_dir = tempfile.mkdtemp(prefix="akaal_test_m2_dur_")
    signing_key = b"test_fencing_signing_key_32bytes!"
    anchor_key = b"test_journal_anchor_key_32bytes!"
    config = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=signing_key,
        journal_anchor_key=anchor_key,
    )
    auth = DurabilityAuthority(config=config)
    try:
        yield auth, temp_dir, signing_key, anchor_key
    finally:
        auth.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_01_cdc_backlog_survives_process_destruction_and_reconstructs(durability_env):
    auth1, temp_dir, signing_key, anchor_key = durability_env
    sess_id = "sess-m2-dur-01"

    # 1. Create CDC backlog buffer bound to DurabilityAuthority
    buffer1 = CDCBacklogBuffer(durability_authority=auth1, session_id=sess_id)

    # 2. Ingest 5 ordered transactional change events
    events = [
        ChangeEvent(
            event_id=f"evt-{i}",
            source_system="ORACLE",
            source_identity="DEVKROS_P8_SRC",
            logical_object="CUSTOMERS",
            operation=ChangeOperation.INSERT if i % 2 == 1 else ChangeOperation.UPDATE,
            source_position=f"100{i}",
            commit_position=f"100{i}",
            commit_timestamp=1700000000.0 + i,
            capture_timestamp=1700000001.0 + i,
            schema_version="v1.0",
            key_columns=("customer_id",),
            key_values={"customer_id": 100 + i},
            before_image=None if i % 2 == 1 else {"customer_id": 100 + i, "name": f"Name_Old_{i}"},
            after_image={"customer_id": 100 + i, "name": f"Name_New_{i}", "val": i * 10},
            tx_context=TransactionContext(tx_id=f"tx-{i}", commit_timestamp_iso="2026-09-25T12:00:00Z", sequence_number=i),
        )
        for i in range(1, 6)
    ]

    for evt in events:
        buffer1.push(evt)

    assert len(buffer1._queue) == 5

    # 3. Simulate process crash / complete destruction of in-memory Python objects
    del buffer1
    auth1.close()

    # 4. Brand-new process restart: reconstruct DurabilityAuthority from disk storage
    config2 = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=signing_key,
        journal_anchor_key=anchor_key,
    )
    auth2 = DurabilityAuthority(config=config2)
    buffer2 = CDCBacklogBuffer(durability_authority=auth2, session_id=sess_id)

    # 5. Recover pending events from durable backend
    recovered = buffer2.recover_pending_events(sess_id)

    # 6. Assert zero event loss, zero corruption, ordering strictly preserved
    assert len(recovered) == 5
    assert len(buffer2._queue) == 5

    for idx, (orig, rec) in enumerate(zip(events, recovered)):
        assert rec.event_id == orig.event_id
        assert rec.operation == orig.operation
        assert rec.logical_object == orig.logical_object
        assert rec.source_position == orig.source_position
        assert rec.key_values == orig.key_values
        assert rec.before_image == orig.before_image
        assert rec.after_image == orig.after_image
        assert rec.tx_context.tx_id == orig.tx_context.tx_id
        assert rec.tx_context.sequence_number == orig.tx_context.sequence_number

    auth2.close()


def test_02_ack_safety_prevents_unrecovered_loss_and_advances_checkpoint(durability_env):
    auth1, temp_dir, signing_key, anchor_key = durability_env
    sess_id = "sess-m2-ack-02"
    mig_id = "mig-p8-m2-ack"

    buffer = CDCBacklogBuffer(durability_authority=auth1, session_id=sess_id)

    # Push 4 events
    for i in range(1, 5):
        buffer.push(ChangeEvent(
            event_id=f"evt-{i}",
            source_system="POSTGRES",
            source_identity="public",
            logical_object="ORDERS",
            operation=ChangeOperation.INSERT,
            source_position=f"0/{i}000",
            commit_position=f"0/{i}000",
            commit_timestamp=1700000000.0 + i,
            capture_timestamp=1700000001.0 + i,
            schema_version="v1.0",
            key_columns=("order_id",),
            key_values={"order_id": i},
            after_image={"order_id": i, "total": 50.0 * i},
        ))

    # Apply & ACK only the first 2 events
    e1 = buffer.pop()
    e2 = buffer.pop()
    buffer.ack_event(e1.event_id)
    buffer.ack_event(e2.event_id)

    # Save checkpoint advancing to e2's position
    token = auth1.issue_fencing_token(mig_id, "worker-1")
    ckpt = MigrationCheckpoint(
        migration_id=mig_id,
        job_id="job-ack",
        fencing_epoch=token.fencing_epoch,
        status="APPLYING",
        metadata={"applied_position": "0/2000", "last_event_id": "evt-2"},
    )
    auth1.save_checkpoint(ckpt, token)

    # Simulate crash
    del buffer
    auth1.close()

    # Reconstruct in fresh process
    config2 = DurabilityConfig(
        storage_dir=temp_dir,
        fencing_signing_key=signing_key,
        journal_anchor_key=anchor_key,
    )
    auth2 = DurabilityAuthority(config=config2)
    buffer_recovered = CDCBacklogBuffer(durability_authority=auth2, session_id=sess_id)
    recovered = buffer_recovered.recover_pending_events(sess_id)

    # Assert only un-ACKed events (evt-3, evt-4) remain in durable backlog
    assert len(recovered) == 2
    assert recovered[0].event_id == "evt-3"
    assert recovered[1].event_id == "evt-4"

    # Assert checkpoint reflects strictly applied boundary
    latest_ckpt = auth2.get_latest_checkpoint(mig_id)
    assert latest_ckpt is not None
    assert latest_ckpt.metadata["applied_position"] == "0/2000"
    assert latest_ckpt.metadata["last_event_id"] == "evt-2"

    auth2.close()


def test_03_failure_injection_across_durability_boundaries(durability_env):
    auth, temp_dir, _, _ = durability_env
    sess_id = "sess-m2-fail-inj"

    buffer = CDCBacklogBuffer(durability_authority=auth, session_id=sess_id)

    # Boundary A: Event pushed to buffer is durably written
    evt = ChangeEvent(
        event_id="evt-inj-1",
        source_system="MYSQL",
        source_identity="db1",
        logical_object="PRODUCTS",
        operation=ChangeOperation.INSERT,
        source_position="gtid-1",
        commit_position="gtid-1",
        commit_timestamp=1700000000.0,
        capture_timestamp=1700000001.0,
        schema_version="v1.0",
        key_columns=("sku",),
        key_values={"sku": "SKU-99"},
        after_image={"sku": "SKU-99", "price": 19.99},
    )
    buffer.push(evt)

    # Verify message exists in durable storage table before in-memory pop
    conn = auth.backend._get_connection()
    cursor = conn.execute("SELECT count(*) FROM queue_records WHERE queue_name = ?;", (f"cdc_backlog_{sess_id}",))
    assert cursor.fetchone()[0] == 1

    # Boundary B: Target apply failure simulated -> event is NOT ACKed
    # Simulate failed apply: we do not call buffer.ack_event()
    # Now simulate recovery
    buffer2 = CDCBacklogBuffer(durability_authority=auth, session_id=sess_id)
    rec = buffer2.recover_pending_events(sess_id)
    assert len(rec) == 1
    assert rec[0].event_id == "evt-inj-1"

    # Boundary C: Successful apply + ACK -> durable record cleanly removed
    buffer2.ack_event("evt-inj-1")
    cursor = conn.execute("SELECT count(*) FROM queue_records WHERE queue_name = ?;", (f"cdc_backlog_{sess_id}",))
    assert cursor.fetchone()[0] == 0
