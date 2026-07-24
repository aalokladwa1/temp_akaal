"""Tests for Failover, Resync, Policy, and Event Bus."""

import pytest
from akaal.replication.services.failover import FailoverManager
from akaal.replication.recovery.resync import AutomaticResynchronizationEngine, IncrementalReplicaRepairEngine, ReplicationRollbackEngine
from akaal.replication.policy.engine import ReplicationPolicyEngine
from akaal.replication.core.config import ReplicationProfile, FailoverMode
from akaal.replication.events.event_bus import ReplicationEventBus, ReplicationMetricsSubscriber
from akaal.replication.events.events import ReplicationEvent, ReplicationEventType


def test_failover_manager():
    fm = FailoverManager()
    res = fm.execute_failover("node_p1", "node_s1")
    assert res["status"] == "FAILOVER_COMPLETED"
    assert res["new_primary"] == "node_s1"


def test_resync_and_rollback_engines():
    resync = AutomaticResynchronizationEngine()
    res = resync.resync_replica("node_sec_01")
    assert res["status"] == "RESYNCHRONIZED"

    rollback = ReplicationRollbackEngine()
    res_rb = rollback.rollback_transaction("txn_9901")
    assert res_rb["status"] == "ROLLED_BACK"


def test_policy_engine_profiles():
    policy_fin = ReplicationPolicyEngine(profile=ReplicationProfile.STRICT_FINANCE)
    res_fin = policy_fin.evaluate_replication(None)
    assert res_fin["requires_approval"] is True
    assert res_fin["approval_level"] == "EXECUTIVE"

    policy_dev = ReplicationPolicyEngine(profile=ReplicationProfile.DEVELOPMENT)
    res_dev = policy_dev.evaluate_replication(None)
    assert res_dev["requires_approval"] is False


@pytest.mark.asyncio
async def test_event_bus():
    bus = ReplicationEventBus()
    sub = ReplicationMetricsSubscriber()
    bus.subscribe_all(sub.on_event)

    await bus.publish(ReplicationEvent(ReplicationEventType.REPLICATION_STARTED, {"domain": "test"}))
    await bus.publish(ReplicationEvent(ReplicationEventType.FAILOVER_COMPLETED, {"primary": "n1"}))

    assert sub.event_counts[ReplicationEventType.REPLICATION_STARTED] == 1
    assert sub.event_counts[ReplicationEventType.FAILOVER_COMPLETED] == 1
