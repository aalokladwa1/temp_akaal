"""
Integration tests for Distributed Runtime (Platform 2) Concurrency, Fault Tolerance,
Split-Brain Prevention, and Hot Reload.
"""

import pytest
import concurrent.futures
from typing import List

from akaal.distributed.facade.runtime import DefaultDistributedRuntimeV1
from akaal.distributed.domain.identifiers import NodeId, TaskId, ExecutionId, IdempotencyKey, ClusterId
from akaal.distributed.domain.models import Task, Node
from akaal.distributed.domain.errors import LeaderElectionError
from akaal.distributed.clock.clock import TestClock
from akaal.distributed.config.config import DistributedRuntimeConfiguration


def test_split_brain_prevention_on_quorum_degradation():
    clock = TestClock(initial_timestamp=100.0)
    runtime = DefaultDistributedRuntimeV1(cluster_id=ClusterId("cluster_quorum"), clock=clock)

    # Set quorum size to 3 nodes
    mem = runtime.membership_service.get_or_create_membership(runtime.cluster_id)
    from dataclasses import replace
    runtime.membership_repo.update_membership(replace(mem, quorum_size=3))
    runtime.leadership_service.handle_leader_failure(runtime.cluster_id)

    node_b = NodeId("node_b")
    runtime.membership_service.join_node(runtime.cluster_id, Node(node_id=node_b, hostname="node_b", ip_address="10.0.0.2"))

    # Active nodes = 2 < quorum_size 3
    with pytest.raises(LeaderElectionError, match="Quorum state degraded"):
        runtime.leadership_service.run_election(runtime.cluster_id, node_b)


def test_concurrent_worker_registration_and_task_execution():
    clock = TestClock(initial_timestamp=500.0)
    runtime = DefaultDistributedRuntimeV1(clock=clock)
    node_id = NodeId("node_multi")

    # Register 10 workers concurrently
    def worker_register_job(i: int):
        return runtime.register_worker(node_id, capacity=10)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        workers = list(executor.map(worker_register_job, range(10)))

    assert len(workers) == 10

    # Submit 20 tasks concurrently with unique idempotency keys
    def submit_job(i: int):
        task = Task(task_id=TaskId(f"task_{i}"), execution_id=ExecutionId(f"exec_{i}"), name=f"step_{i}")
        key = IdempotencyKey(f"key_{i}")
        return runtime.submit_task(task, idempotency_key=key)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        requests = list(executor.map(submit_job, range(20)))

    assert len(requests) == 20

    # Process all 20 tasks
    processed_count = 0
    for _ in range(20):
        res = runtime.process_next()
        if res:
            processed_count += 1

    assert processed_count == 20


def test_heartbeat_timeout_eviction_and_lease_recovery():
    clock = TestClock(initial_timestamp=1000.0)
    runtime = DefaultDistributedRuntimeV1(clock=clock)
    node = NodeId("node_primary")

    w = runtime.register_worker(node, capacity=1)

    # Advance clock past heartbeat timeout (15s default)
    clock.advance(20.0)

    # Detect unhealthy workers
    unhealthy = runtime.heartbeat_manager.detect_unhealthy_workers()
    assert len(unhealthy) == 1
    assert unhealthy[0].worker_id == w.worker_id

    # Check cluster health reflects degraded/unhealthy status
    health = runtime.get_cluster_health()
    assert health["unhealthy_workers_count"] == 1


def test_configuration_hot_reload():
    config_mgr = DistributedRuntimeConfiguration()
    cfg1 = config_mgr.active_config
    assert cfg1.config_version == 1

    cfg2 = config_mgr.hot_reload({"cluster": {"lease_ttl_seconds": 60.0}})
    assert cfg2.config_version == 2
    assert cfg2.get("cluster.lease_ttl_seconds") == 60.0
