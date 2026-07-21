"""
Unit tests for Feature 2 — Dynamic Metadata Refresh.
"""

import time
import pytest

from akaal.schema.domain.enums import RefreshState
from akaal.schema.domain.identifiers import SnapshotID, VersionID
from akaal.schema.observability.event_bus import SchemaEventPublisher
from akaal.schema.refresh.cache import ThreadSafeMetadataCache
from akaal.schema.refresh.coordinator import RefreshCoordinator
from akaal.schema.refresh.service import MetadataRefreshService
from akaal.schema.versioning.manager import MetadataVersionManager
from akaal.schema.versioning.snapshot import SchemaSnapshot


def test_thread_safe_metadata_cache_ttl_and_hit_ratio():
    cache = ThreadSafeMetadataCache(default_ttl_seconds=0.05)
    snap = SchemaSnapshot(snapshot_id=SnapshotID.generate(), version_id=VersionID.generate(), tables={"t1": {}})
    cache.put(snap)

    assert cache.get() == snap
    assert cache.get_hit_ratio() == 1.0

    time.sleep(0.06)
    assert cache.get() is None
    assert cache.get_hit_ratio() == 0.5


def test_refresh_coordinator_single_flight_and_state_machine():
    coord = RefreshCoordinator()
    assert coord.state_machine.state == RefreshState.IDLE

    assert coord.acquire_refresh_lock() is True
    assert coord.state_machine.state == RefreshState.REFRESHING

    # Single-flight check: second acquire fails
    assert coord.acquire_refresh_lock() is False

    coord.release_refresh_lock(success=True)
    assert coord.state_machine.state == RefreshState.COMPLETED


def test_metadata_refresh_service_events_and_discovery():
    events_received = []
    bus = SchemaEventPublisher()
    bus.subscribe("METADATA_REFRESHED", lambda e: events_received.append(e))

    vm = MetadataVersionManager()
    service = MetadataRefreshService(
        version_manager=vm,
        event_publisher=bus,
        discovery_func=lambda: {"discovered_table": {"columns": []}},
    )

    snap = service.refresh(source="unit_test")
    assert snap is not None
    assert "discovered_table" in snap.tables
    assert len(events_received) == 1
    assert events_received[0].payload["source"] == "unit_test"
