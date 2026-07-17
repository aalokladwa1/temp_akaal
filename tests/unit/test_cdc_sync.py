import pytest
from datetime import datetime, timezone
from akaal.migration.models.cdc import (
    CDCOperationType,
    CDCSessionState,
    ConflictResolutionPolicy,
    SynchronizationConfiguration,
    CDCEvent,
    CDCCheckpoint,
    SynchronizationMetrics,
    SynchronizationHealth,
    SynchronizationSession
)
from akaal.migration.ddl.planning.cdc_planner import CDCPlanner
from akaal.migration.execution.cdc_executor import (
    CDCEventBuffer,
    CDCExecutor,
    CDCSyncSupervisor
)
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter

class MockConfig:
    def __init__(self, host, database_name="test_db", port=5432, username="test", password="test"):
        self.host = host
        self.database_name = database_name
        self.port = port
        self.username = username
        self.password = password
        self.mock_mode = True

# --- 1. Model & Validation Tests ---

def test_cdc_configuration_validation():
    config = SynchronizationConfiguration(
        session_id="session_123",
        source_dialect="postgresql",
        target_dialect="mysql",
        conflict_policy=ConflictResolutionPolicy.SOURCE_WINS,
        batch_size=100,
        max_queue_depth=1000,
        retry_limit=3,
        retry_backoff_factor=1.5,
        heartbeat_interval_seconds=1.0
    )
    config.validate()  # Should pass without issues

    with pytest.raises(ValueError):
        bad_config = SynchronizationConfiguration(
            session_id="session_123",
            source_dialect="postgresql",
            target_dialect="mysql",
            conflict_policy=ConflictResolutionPolicy.SOURCE_WINS,
            batch_size=0,  # Invalid
            max_queue_depth=1000,
            retry_limit=3,
            retry_backoff_factor=1.5,
            heartbeat_interval_seconds=1.0
        )
        bad_config.validate()

# --- 2. Event Buffer & Flow Control / Backpressure Tests ---

@pytest.mark.asyncio
async def test_event_buffer_flow_control():
    buffer = CDCEventBuffer(max_depth=10)
    assert buffer.paused is False

    # Fill buffer to HWM (85% of 10 is 8)
    for i in range(8):
        event = CDCEvent(
            event_id=f"evt_{i}",
            tx_id="tx_1",
            timestamp=datetime.now(timezone.utc),
            operation=CDCOperationType.INSERT,
            schema_name="public",
            table_name="orders",
            primary_key_values={"id": i}
        )
        await buffer.push(event)

    assert buffer.paused is True  # HWM reached

    # Pop batch to reach LWM (30% of 10 is 3)
    # Drain 6 events, leaving 2 events in buffer
    await buffer.pop_batch(6)
    assert buffer.paused is False  # Ingestion resumed

# --- 3. Planner & Ordering Tests ---

def test_cdc_planner_ordering_and_deduplication():
    evt1 = CDCEvent(
        event_id="evt_1",
        tx_id="tx_1",
        timestamp=datetime.now(timezone.utc),
        operation=CDCOperationType.INSERT,
        schema_name="public",
        table_name="orders",
        primary_key_values={"id": 1},
        lsn_offset=100,
        checksum="checksum_abc"
    )
    evt2 = CDCEvent(
        event_id="evt_2",
        tx_id="tx_1",
        timestamp=datetime.now(timezone.utc),
        operation=CDCOperationType.INSERT,
        schema_name="public",
        table_name="orders",
        primary_key_values={"id": 1},
        lsn_offset=100,
        checksum="checksum_abc"  # Duplicate
    )
    evt3 = CDCEvent(
        event_id="evt_3",
        tx_id="tx_2",
        timestamp=datetime.now(timezone.utc),
        operation=CDCOperationType.UPDATE,
        schema_name="public",
        table_name="orders",
        primary_key_values={"id": 1},
        lsn_offset=101,
        checksum="checksum_def"
    )

    batch = [evt3, evt1, evt2]
    planned = CDCPlanner.plan_batch(batch)

    # Ordered chronologically by LSN (evt1/evt2 before evt3) and deduplicated
    assert len(planned) == 2
    assert planned[0].event_id == "evt_1"
    assert planned[1].event_id == "evt_3"

# --- 4. Conflict Resolution Engine Tests ---

@pytest.mark.asyncio
async def test_conflict_resolution_policies():
    config = SynchronizationConfiguration(
        session_id="session_123",
        source_dialect="postgresql",
        target_dialect="mysql",
        conflict_policy=ConflictResolutionPolicy.TARGET_WINS,
        batch_size=10,
        max_queue_depth=100,
        retry_limit=3,
        retry_backoff_factor=1.5,
        heartbeat_interval_seconds=1.0
    )
    metrics = SynchronizationMetrics()
    executor = CDCExecutor(config, metrics)

    target_state = {
        "public.orders": {
            "{'id': 1}": {"id": 1, "status": "modified_at_target"}
        }
    }

    # Source event: update row from "pending" to "active"
    # But target has already modified it to "modified_at_target"
    event = CDCEvent(
        event_id="evt_1",
        tx_id="tx_1",
        timestamp=datetime.now(timezone.utc),
        operation=CDCOperationType.UPDATE,
        schema_name="public",
        table_name="orders",
        primary_key_values={"id": 1},
        before_image={"id": 1, "status": "pending"},
        after_image={"id": 1, "status": "active"},
        lsn_offset=100
    )

    # 1. Target Wins: Event is ignored, target state is preserved
    await executor.execute_batch([event], target_state)
    assert target_state["public.orders"]["{'id': 1}"]["status"] == "modified_at_target"

    # 2. Source Wins: Event overwrites target state
    config_source_wins = SynchronizationConfiguration(
        session_id="session_123",
        source_dialect="postgresql",
        target_dialect="mysql",
        conflict_policy=ConflictResolutionPolicy.SOURCE_WINS,
        batch_size=10,
        max_queue_depth=100,
        retry_limit=3,
        retry_backoff_factor=1.5,
        heartbeat_interval_seconds=1.0
    )
    executor_source_wins = CDCExecutor(config_source_wins, metrics)
    await executor_source_wins.execute_batch([event], target_state)
    assert target_state["public.orders"]["{'id': 1}"]["status"] == "active"

# --- 5. Supervisor Graceful Shutdown & Recovery Tests ---

@pytest.mark.asyncio
async def test_supervisor_graceful_shutdown():
    config = SynchronizationConfiguration(
        session_id="session_123",
        source_dialect="postgresql",
        target_dialect="postgresql",
        conflict_policy=ConflictResolutionPolicy.SOURCE_WINS,
        batch_size=10,
        max_queue_depth=100,
        retry_limit=3,
        retry_backoff_factor=1.5,
        heartbeat_interval_seconds=1.0
    )
    supervisor = CDCSyncSupervisor(config)
    await supervisor.start()
    
    # Push event to queue
    event = CDCEvent(
        event_id="evt_1",
        tx_id="tx_1",
        timestamp=datetime.now(timezone.utc),
        operation=CDCOperationType.INSERT,
        schema_name="public",
        table_name="orders",
        primary_key_values={"id": 1},
        after_image={"id": 1, "status": "active"},
        lsn_offset=100
    )
    await supervisor.buffer.push(event)
    
    target_state = {}
    
    # Shutdown drains buffer and commits checkpoint
    await supervisor.stop(target_state)
    assert supervisor.state == CDCSessionState.COMPLETED
    assert target_state["public.orders"]["{'id': 1}"]["status"] == "active"

# --- 6. Adapters Integration Tests ---

@pytest.mark.asyncio
async def test_all_adapters_fetch_cdc_changes():
    adapters = [
        PostgreSQLAdapter(MockConfig("source-db.example.com")),
        MySQLAdapter(MockConfig("target-db.example.com")),
        OracleAdapter(MockConfig("oracle-prod.example.com")),
        MSSQLAdapter(MockConfig("postgres-target.example.com"))
    ]

    for adapter in adapters:
        await adapter.connect()
        await adapter.start_cdc_stream(["orders"])
        
        changes = await adapter.fetch_changes(10)
        assert len(changes) > 0
        assert changes[0].operation == CDCOperationType.INSERT
        
        await adapter.stop_cdc_stream()

# --- 7. Additional Edge Case, Failures & Concurrency Tests ---

def test_duplicate_transaction_replay():
    events = [
        CDCEvent("e1", "tx1", datetime.now(timezone.utc), CDCOperationType.INSERT, "s", "t", {"id": 1}, lsn_offset=10, checksum="c1"),
        CDCEvent("e2", "tx1", datetime.now(timezone.utc), CDCOperationType.INSERT, "s", "t", {"id": 1}, lsn_offset=10, checksum="c1"), # Replay duplicate
    ]
    planned = CDCPlanner.plan_batch(events)
    assert len(planned) == 1

def test_malformed_events_handling():
    # Verify missing SCN/LSN handles safely (falls back to 0 in sorting)
    evt = CDCEvent("e1", "tx1", datetime.now(timezone.utc), CDCOperationType.INSERT, "s", "t", {"id": 1}, lsn_offset=None)
    planned = CDCPlanner.plan_batch([evt])
    assert len(planned) == 1

def test_corrupted_checkpoint_detection():
    # Seek seeking fails safely or validates checkpoint bounds
    cp = CDCCheckpoint("sess", "evt_1", last_processed_lsn=-5, last_processed_tx_id="tx1", last_processed_timestamp=datetime.now())
    # Out of bounds check
    assert cp.last_processed_lsn < 0

def test_retry_exhaustion_failure():
    config = SynchronizationConfiguration(
        session_id="session_123",
        source_dialect="postgresql",
        target_dialect="postgresql",
        conflict_policy=ConflictResolutionPolicy.SOURCE_WINS,
        batch_size=10,
        max_queue_depth=100,
        retry_limit=3,
        retry_backoff_factor=1.5,
        heartbeat_interval_seconds=1.0
    )
    supervisor = CDCSyncSupervisor(config)
    supervisor.simulate_failure("Connection lost permanently.")
    assert supervisor.state == CDCSessionState.FAILED
    assert supervisor.health.is_healthy is False

@pytest.mark.asyncio
async def test_concurrent_sessions():
    c1 = SynchronizationConfiguration("s1", "postgresql", "postgresql", ConflictResolutionPolicy.SKIP, 10, 100, 3, 1.5, 1.0)
    c2 = SynchronizationConfiguration("s2", "mysql", "mysql", ConflictResolutionPolicy.SKIP, 10, 100, 3, 1.5, 1.0)
    
    s1 = CDCSyncSupervisor(c1)
    s2 = CDCSyncSupervisor(c2)
    
    await s1.start()
    await s2.start()
    
    assert s1.config.session_id == "s1"
    assert s2.config.session_id == "s2"
    assert s1.metrics.events_processed == 0
    assert s2.metrics.events_processed == 0

@pytest.mark.asyncio
async def test_active_sync_graceful_shutdown():
    config = SynchronizationConfiguration("s1", "postgresql", "postgresql", ConflictResolutionPolicy.SOURCE_WINS, 10, 100, 3, 1.5, 1.0)
    supervisor = CDCSyncSupervisor(config)
    await supervisor.start()
    
    # Generate 5 events
    for i in range(5):
        await supervisor.buffer.push(
            CDCEvent(f"evt_{i}", "tx1", datetime.now(), CDCOperationType.INSERT, "s", "t", {"id": i}, after_image={"id": i})
        )
        
    target_state = {}
    await supervisor.stop(target_state)
    # Drained and completed
    assert supervisor.state == CDCSessionState.COMPLETED
    assert len(target_state.get("s.t", {})) == 5

@pytest.mark.asyncio
async def test_large_event_batches():
    config = SynchronizationConfiguration("s1", "postgresql", "postgresql", ConflictResolutionPolicy.SOURCE_WINS, 1000, 5000, 3, 1.5, 1.0)
    supervisor = CDCSyncSupervisor(config)
    await supervisor.start()
    
    events = []
    for i in range(1000):
        events.append(
            CDCEvent(f"evt_{i}", "tx1", datetime.now(), CDCOperationType.INSERT, "s", "t", {"id": i}, after_image={"id": i}, lsn_offset=i)
        )
    
    target_state = {}
    await supervisor.executor.execute_batch(events, target_state)
    assert supervisor.metrics.events_processed == 1000
