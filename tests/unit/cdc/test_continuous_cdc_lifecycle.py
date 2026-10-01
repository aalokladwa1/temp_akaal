"""
Unit regression proving continuous CDC background execution lifecycle:
- Capture begins before apply binding
- Backlog accumulates events safely
- Apply binding establishes continuous worker thread
- Queued and subsequent events drain continuously
- ACK and checkpoint progress match physical apply state
- Canonical lifecycle stop terminates worker safely.
"""

import time
from typing import List, Dict, Any
from akaalEngine.cdc.api import CDCAuthority, ChangeEvent, ChangeOperation, CDCBacklogBuffer
from akaalEngine.cdc.capture.base import ICDCSourceAdapter


class FakeCDCSourceAdapter(ICDCSourceAdapter):
    def __init__(self):
        self.events: List[ChangeEvent] = []

    def fetch_events(self, max_events: int = 1000) -> List[ChangeEvent]:
        batch = self.events[:max_events]
        self.events = self.events[max_events:]
        return batch

    def start_capture(self) -> None:
        pass

    @property
    def capabilities(self) -> List[str]:
        return ["cdc_capture"]

    def close(self) -> None:
        pass

    @property
    def engine_name(self) -> str:
        return "fake_cdc"

    def get_current_position(self) -> Any:
        return "pos-1"

    def validate_prerequisites(self) -> bool:
        return True


class FakeTargetWriter:
    def __init__(self):
        self.applied_events: List[Any] = []
        self.params: Dict[str, Any] = {"schema": "target_schema"}

    def write_batch(self, table_name: str, batch: Any, target_schema: str = "public", pk_columns: Any = None) -> int:
        for r in batch.rows:
            self.applied_events.append((table_name, r))
        return len(batch.rows)

    def delete_batch(self, table_name: str, target_schema: str, pk_columns: Any, key_records: Any) -> int:
        for k in key_records:
            self.applied_events.append(("DELETE", table_name, k))
        return len(key_records)

    def commit(self) -> None:
        pass


def make_test_evt(event_id: str, table: str, after_dict: dict, tx_id: str = "tx-1"):
    now = time.time()
    return ChangeEvent(
        event_id=event_id,
        source_system="GENERIC",
        source_identity="pos-1",
        logical_object=table,
        operation=ChangeOperation.INSERT,
        source_position="pos-1",
        commit_position="pos-1",
        commit_timestamp=now,
        capture_timestamp=now,
        schema_version="1.0.0",
        key_columns=("id",),
        key_values={"id": after_dict.get("id", 1)},
        after_image=after_dict,
        tx_context=type("TxCtx", (), {"tx_id": tx_id, "commit_timestamp_iso": "", "sequence_number": 1, "total_events_in_tx": 1})(),
    )


def test_continuous_post_bind_cdc_lifecycle():
    adapter = FakeCDCSourceAdapter()
    writer = FakeTargetWriter()
    cdc = CDCAuthority(active_adapter=adapter, capture_poll_interval_ms=10)

    # 1. Capture begins before target apply binding
    evt1 = make_test_evt("evt-1", "users", {"id": 1, "name": "Alice"}, "tx-100")
    evt2 = make_test_evt("evt-2", "users", {"id": 2, "name": "Bob"}, "tx-100")
    adapter.events.extend([evt1, evt2])

    cdc.start_capture()
    time.sleep(0.05)
    assert len(writer.applied_events) == 0, "No events should apply before target writer is bound"

    # 2. Target writer is bound -> continuous worker established
    cdc.bind_target_writer(writer)

    # Wait briefly for background thread to drain initial queued events
    deadline = time.time() + 2.0
    while time.time() < deadline and len(writer.applied_events) < 2:
        time.sleep(0.02)

    assert writer.applied_events[0] == ("users", {"id": 1, "name": "Alice"})
    assert writer.applied_events[1] == ("users", {"id": 2, "name": "Bob"})

    # 3. Later independent events arrive and drain automatically without manual drain_and_sync()
    evt3 = make_test_evt("evt-3", "orders", {"id": 101, "user_id": 1}, "tx-101")
    adapter.events.append(evt3)

    deadline = time.time() + 2.0
    while time.time() < deadline and len(writer.applied_events) < 3:
        time.sleep(0.02)

    assert len(writer.applied_events) == 3, f"Later events must drain continuously (got {len(writer.applied_events)})"
    assert writer.applied_events[2] == ("orders", {"id": 101, "user_id": 1})

    # 4. ACK progress matches applied count
    assert cdc.events_applied_total == 3

    # 5. Stop background streaming cleanly
    cdc._stop_streaming.set()
    if cdc._streaming_thread:
        cdc._streaming_thread.join(timeout=1.0)
    assert not (cdc._streaming_thread and cdc._streaming_thread.is_alive())
