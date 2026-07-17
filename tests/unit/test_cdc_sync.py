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
