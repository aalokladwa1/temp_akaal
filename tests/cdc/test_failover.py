"""
Unit tests for Failover Synchronization and Worker Lease Manager.
"""

import pytest
from akaal.cdc.failover.coordinator import CDCFailoverCoordinator, WorkerFailoverManager


@pytest.mark.asyncio
async def test_worker_failover_manager():
    mgr = WorkerFailoverManager()
    mgr.acquire_lease("node-1", "stream-alpha")
    mgr.acquire_lease("node-1", "stream-beta")

    recovered = mgr.failover_lease("node-1", "node-2")
    assert recovered == 2


@pytest.mark.asyncio
async def test_cdc_failover_coordinator():
    coord = CDCFailoverCoordinator()
    coord.worker_manager.acquire_lease("worker-a", "stream-1")

    res = await coord.trigger_failover("worker-a", "worker-b")
    assert res.node_id == "worker-b"
    assert res.status == "COMPLETED"
    assert res.recovered_session_count == 1
