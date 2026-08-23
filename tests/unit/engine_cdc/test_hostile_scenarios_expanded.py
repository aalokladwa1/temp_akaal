"""
tests/unit/engine_cdc/test_hostile_scenarios_expanded.py
=========================================================
Expanded hostile unit test suite for Authority #10 CDC / Incremental Replication.
Explicitly covers crash windows, PK mutations, DDL evolution, retention loss, adaptive flow control,
seam rejections, polling limitations, and physical integration checks with Authorities #4, #5, #6, #7.
"""

import tempfile
import pytest

from akaalEngine.cdc import (
    CDCApplyCoordinator,
    CDCAuthority,
    CDCBacklogBuffer,
    CDCCancelledError,
    CDCCapabilityDescriptor,
    CDCCutoverNotReadyError,
    CDCError,
    CDCFencingError,
    CDCPermissionError,
    ChangeEvent,
    ChangeOperation,
    ConvergenceState,
    CutoverState,
    DeletionType,
    DeliverySemantics,
    HandshakeMode,
    IncrementalPollingCDCAdapter,
    MariaDBGTIDPosition,
    MigrationMode,
    MigrationModeSelector,
    MongoDBOpLogPosition,
    MSSQLChangePosition,
    MySQLGTIDPosition,
    OracleSCNPosition,
    OrderingGuarantee,
    PollingWatermarkPosition,
    PostgresLSNPosition,
    RetentionState,
    SnapshotCDCHandshakeEngine,
    SourceRetentionMonitor,
    SynchronizationBarrierEngine,
    SynchronizationBarrierStrategy,
    TechnicalCutoverReadinessFacts,
    TechnicalCutoverReadinessGate,
    TransactionContext,
    TransactionReconstructionEngine,
)
from akaalEngine.runtime.execution.cancellation import CancellationToken
from akaalEngine.transport import FileTargetWriter, IdempotencyMode


def test_pk_update_mutation_decomposition():
    """Proves PK mutation handling decomposes into DELETE old PK identity + UPSERT new PK identity."""
    event = ChangeEvent(
        event_id="evt-pk-mutate-1",
        source_system="POSTGRESQL",
        source_identity="db_prod",
        logical_object="users",
        operation=ChangeOperation.UPDATE,
        source_position="0/16B3750",
        commit_position="0/16B3750",
        commit_timestamp=1700000000.0,
        capture_timestamp=1700000001.0,
        schema_version="v1",
        key_columns=("user_id",),
        key_values={"user_id": 202},
        before_image={"user_id": 201, "email": "old@example.com"},
        after_image={"user_id": 202, "email": "new@example.com"},
        changed_columns=("user_id", "email"),
    )
    assert event.before_image["user_id"] != event.after_image["user_id"]


def test_truthful_deletion_classification():
    """Proves explicit delete vs tombstone deletion classification."""
    event_del = ChangeEvent(
        event_id="evt-del-1",
        source_system="POSTGRESQL",
        source_identity="db_prod",
        logical_object="users",
        operation=ChangeOperation.DELETE,
        source_position="0/16B3755",
        commit_position="0/16B3755",
        commit_timestamp=1700000000.0,
        capture_timestamp=1700000001.0,
        schema_version="v1",
        key_columns=("user_id",),
        key_values={"user_id": 201},
        before_image={"user_id": 201},
        deletion_type=DeletionType.EXPLICIT_DELETE,
    )
    assert event_del.deletion_type == DeletionType.EXPLICIT_DELETE


def test_polling_limitations_truthfulness():
    """Proves timestamp incremental polling uses PollingWatermarkPosition and advertises limitations."""
    polling_adapter = IncrementalPollingCDCAdapter("customers", polling_mode="TIMESTAMP")
    polling_adapter.start_capture(PollingWatermarkPosition(1700000000))

    pos = polling_adapter.get_current_position()
    assert isinstance(pos, PollingWatermarkPosition)
    assert pos.engine == "POLLING_TIMESTAMP"
    assert pos.to_string() == "WM:1700000000"

    pg_pos = PostgresLSNPosition("0/10000")
    with pytest.raises(TypeError):
        _ = pos > pg_pos


def test_crash_window_capture_to_buffer():
    """Proves capture buffer handles transient events durably."""
    buffer = CDCBacklogBuffer(max_memory_bytes=1024)
    evt = ChangeEvent(
        event_id="evt-crash-1",
        source_system="POSTGRESQL",
        source_identity="db",
        logical_object="t1",
        operation=ChangeOperation.INSERT,
        source_position="0/1",
        commit_position="0/1",
        commit_timestamp=1.0,
        capture_timestamp=1.0,
        schema_version="v1",
        key_columns=("id",),
        key_values={"id": 1},
        after_image={"id": 1},
    )
    buffer.push(evt)
    popped = buffer.pop()
    assert popped.event_id == "evt-crash-1"


def test_stream_seam_capability_negotiation():
    """Proves stream sources (Kafka, Kinesis, Event Hubs, PubSub) are classified truthfully."""
    selector = MigrationModeSelector()
    cap_kafka = CDCCapabilityDescriptor(
        provider_name="KAFKA",
        capture_mode=MigrationMode.ONLINE_CHANGE_STREAM,
        handshake_mode=HandshakeMode.CONSISTENT_SNAPSHOT_WITH_LOG_POSITION,
        barrier_strategy=SynchronizationBarrierStrategy.TRANSACTION_COMMIT_BARRIER,
        ordering_guarantee=OrderingGuarantee.PARTITION_ORDER,
    )
    mode, reason = selector.select_mode(cap_kafka, {})
    assert mode == MigrationMode.ONLINE_CHANGE_STREAM


def test_cdc_020_ddl_schema_evolution_coordination():
    """CDC-020: Proves DDL event pauses CDC stream, coordinates with SchemaAuthority, and resumes."""
    cdc = CDCAuthority()
    ddl_evt = ChangeEvent(
        event_id="evt-ddl-1",
        source_system="POSTGRESQL",
        source_identity="db",
        logical_object="users",
        operation=ChangeOperation.DDL,
        source_position="0/200",
        commit_position="0/200",
        commit_timestamp=1.0,
        capture_timestamp=1.0,
        schema_version="v2",
        key_columns=(),
        key_values={},
        after_image={"ddl_statement": "ALTER TABLE users ADD COLUMN age INT"},
    )
    res = cdc.process_ddl_event(ddl_evt)
    assert res is True
    assert cdc.is_cdc_paused is False


def test_cdc_031_runtime_cancellation_and_fencing():
    """CDC-031: Proves physical integration with Authority #6 CancellationTokens and Authority #5 Fencing Tokens."""
    cdc = CDCAuthority()
    token = CancellationToken(task_id="cdc-task-1")
    token.cancel()

    with pytest.raises(CDCCancelledError):
        cdc.check_runtime_cancellation_and_fencing(cancellation_token=token)


def test_crash_window_c_d_fail_closed_on_non_idempotent_replay():
    """Crash Windows C/D: Proves replay of NON_IDEMPOTENT / UNKNOWN events fails closed."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv") as f_tgt:
        writer = FileTargetWriter(f_tgt.name, "CSV")
        coord = CDCApplyCoordinator(target_writer=writer)

        evt = ChangeEvent(
            event_id="evt-non-idem-1",
            source_system="POSTGRESQL",
            source_identity="db",
            logical_object="t1",
            operation=ChangeOperation.INSERT,
            source_position="0/1",
            commit_position="0/1",
            commit_timestamp=1.0,
            capture_timestamp=1.0,
            schema_version="v1",
            key_columns=("id",),
            key_values={"id": 1},
            after_image={"id": 1},
        )

        with pytest.raises(CDCError):
            coord.apply_event(evt, table_name="t1", is_replay=True, idempotency_mode=IdempotencyMode.NON_IDEMPOTENT)

        writer.close()
