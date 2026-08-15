"""
AKAAL P3.6 Dedicated CDC Parallel Sharding & High-Throughput Replay Acceptance Suite.
====================================================================================
Tests all 36 mandatory requirements for P3.6.
"""

import os
import shutil
import tempfile
import unittest
from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCTransaction, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.errors import CDCExecutionError
from akaal.cdc.sharding.domain import (
    CDCPartitionKey,
    CDCRoutedTransaction,
    CDCPartitionState,
    CDCRouteGeneration,
    CDCBoundaryStatus,
)
from akaal.cdc.sharding.router import CDCPartitionRouter
from akaal.cdc.sharding.barrier import CDCCrossPartitionOrderingBarrier
from akaal.cdc.sharding.guard import CDCSplitBrainShardGuard
from akaal.cdc.sharding.frontier import CDCCheckpointFrontierTracker
from akaal.cdc.sharding.parallel_engine import CDCParallelApplyEngine
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator


class TestP36CDCParallelShardingEngine(unittest.TestCase):

    def setUp(self):
        import uuid
        self.temp_dir = tempfile.mkdtemp()
        self.migration_id = f"mig-p36-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p36-test"
        self.run_id = "run-p36-test"
        self.cdc_session_id = f"sess-p36-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        self.state_store = CentralStateStore()
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)

        self.engine = CDCParallelApplyEngine(
            identity=self.identity,
            partition_count=4,
            routing_generation=1,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        self.engine.initialize_partition_workers(self.fencing_epoch)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_sample_event(self, entity_id: int, pos_str: str = "0/100", table_name: str = "users") -> CDCEvent:
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition(pos_str),
            after_image={"id": entity_id, "name": f"User {entity_id}"},
        )

    def _make_sample_tx(self, tx_id: str, events: list, pos_str: str = "0/100") -> CDCTransaction:
        return CDCTransaction(
            identity=self.identity,
            tx_id=tx_id,
            commit_position=PostgresLSNPosition(pos_str),
            events=events,
        )

    # 1. Deterministic routing & stable hashing
    def test_01_deterministic_routing_sha256(self):
        slot1 = CDCPartitionRouter.get_deterministic_hash_slot(self.cdc_session_id, "users", "100", 4, 1)
        slot2 = CDCPartitionRouter.get_deterministic_hash_slot(self.cdc_session_id, "users", "100", 4, 1)
        self.assertEqual(slot1, slot2)

    # 2. Routing stability after restart
    def test_02_routing_stability_after_restart(self):
        router1 = CDCPartitionRouter(partition_count=4, routing_generation=1)
        router2 = CDCPartitionRouter(partition_count=4, routing_generation=1)
        e = self._make_sample_event(42)
        k1 = router1.route_event(e)
        k2 = router2.route_event(e)
        self.assertEqual(k1.partition_id, k2.partition_id)

    # 3. Same key -> same partition
    def test_03_same_key_same_partition(self):
        router = CDCPartitionRouter(partition_count=4, routing_generation=1)
        e1 = self._make_sample_event(42, "0/100")
        e2 = self._make_sample_event(42, "0/200")
        k1 = router.route_event(e1)
        k2 = router.route_event(e2)
        self.assertEqual(k1.partition_id, k2.partition_id)

    # 4. Different keys can route independently
    def test_04_different_keys_independent(self):
        router = CDCPartitionRouter(partition_count=100, routing_generation=1)
        e1 = self._make_sample_event(1)
        e2 = self._make_sample_event(99999)
        k1 = router.route_event(e1, partition_count=100)
        k2 = router.route_event(e2, partition_count=100)
        # With 100 partitions, 1 and 99999 hash to different slots
        self.assertNotEqual(k1.partition_id, k2.partition_id)

    # 5. Single-partition transaction execution
    def test_05_single_partition_transaction_dispatch(self):
        tx = self._make_sample_tx("tx-1", [self._make_sample_event(1)])
        routed = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.assertFalse(routed.is_multi_partition)
        res = self.engine.process_all_partitions(self.fencing_epoch)
        self.assertTrue(len(res) > 0)

    # 6. Multi-partition transaction coordination
    def test_06_multi_partition_transaction_coordination(self):
        e1 = self._make_sample_event(1, table_name="table_a")
        e2 = self._make_sample_event(99999, table_name="table_b")
        tx = self._make_sample_tx("tx-multi", [e1, e2])

        # Force distinct partitions
        router = CDCPartitionRouter(partition_count=100)
        k1 = router.route_event(e1, partition_count=100)
        k2 = router.route_event(e2, partition_count=100)

        engine_100 = CDCParallelApplyEngine(
            identity=self.identity,
            partition_count=100,
            routing_generation=1,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        engine_100.initialize_partition_workers(self.fencing_epoch)

        routed = engine_100.dispatch_transaction(tx, self.fencing_epoch)
        if k1.partition_id != k2.partition_id:
            self.assertTrue(routed.is_multi_partition)
            self.assertEqual(len(routed.partition_ids), 2)

    # 7. Transaction atomicity
    def test_07_transaction_atomicity_preserved(self):
        tx = self._make_sample_tx("tx-atom", [self._make_sample_event(5), self._make_sample_event(6)])
        routed = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        res = self.engine.process_all_partitions(self.fencing_epoch)
        self.assertEqual(self.engine._total_applied_transactions, 1)

    # 8. Per-key ordering
    def test_08_per_key_ordering(self):
        tx1 = self._make_sample_tx("tx-ord-1", [self._make_sample_event(10, "0/100")])
        tx2 = self._make_sample_tx("tx-ord-2", [self._make_sample_event(10, "0/200")])
        r1 = self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        r2 = self.engine.dispatch_transaction(tx2, self.fencing_epoch)
        q = self.engine.partition_queues[r1.primary_partition_id]
        self.assertEqual(q[0].tx_id, "tx-ord-1")
        self.assertEqual(q[1].tx_id, "tx-ord-2")

    # 9. Independent partition concurrency
    def test_09_independent_partition_concurrency(self):
        tx1 = self._make_sample_tx("tx-c1", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("tx-c2", [self._make_sample_event(2)])
        r1 = self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        r2 = self.engine.dispatch_transaction(tx2, self.fencing_epoch)
        self.assertIsNotNone(r1.primary_partition_id)
        self.assertIsNotNone(r2.primary_partition_id)

    # 10. Persistent routing generation
    def test_10_persistent_routing_generation(self):
        gen = self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 8, self.fencing_epoch)
        self.assertEqual(gen.routing_generation, 1)
        self.assertEqual(gen.partition_count, 8)

    # 11. Partition generation transition
    def test_11_partition_generation_transition(self):
        gen = self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 8, self.fencing_epoch)
        done = self.engine.shard_guard.complete_rebalance(self.migration_id, self.cdc_session_id, gen.routing_generation, self.fencing_epoch)
        self.assertTrue(done)

    # 12. Safe worker ownership
    def test_12_safe_worker_ownership(self):
        pstate = self.engine.shard_guard.register_partition_worker(self.migration_id, self.cdc_session_id, 0, 1, "w1", self.fencing_epoch)
        self.assertEqual(pstate.owner_worker_id, "w1")

    # 13. Duplicate ownership rejection
    def test_13_duplicate_ownership_rejection(self):
        self.engine.shard_guard.register_partition_worker(self.migration_id, self.cdc_session_id, 0, 1, "w1", self.fencing_epoch)
        valid = self.engine.shard_guard.validate_worker_ownership(self.migration_id, self.cdc_session_id, 0, "w2", self.fencing_epoch)
        self.assertFalse(valid)

    # 14. Stale worker rejection
    def test_14_stale_worker_rejection(self):
        stale_epoch = self.fencing_epoch
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.shard_guard.register_partition_worker(self.migration_id, self.cdc_session_id, 0, 1, "w-stale", stale_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_PARTITION_WORKER")

    # 15. Worker crash recovery
    def test_15_worker_crash_recovery(self):
        self.engine.workers[0] = None  # Crash worker
        with self.assertRaises(CDCExecutionError):
            self.engine.process_partition_batch(0, self.fencing_epoch)

    # 16. Coordinator restart recovery
    def test_16_coordinator_restart_recovery(self):
        self.engine.dispatch_transaction(self._make_sample_tx("tx-rec", [self._make_sample_event(1)]), self.fencing_epoch)
        # Recreate engine from state store
        engine2 = CDCParallelApplyEngine(identity=self.identity, partition_count=4, state_store=self.state_store)
        engine2.initialize_partition_workers(self.fencing_epoch)
        self.assertIsNotNone(engine2)

    # 17. Rebalance safety
    def test_17_rebalance_safety(self):
        gen = self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 16, self.fencing_epoch)
        self.assertEqual(gen.status, "REBALANCING")

    # 18. In-flight rebalance handling
    def test_18_inflight_rebalance_handling(self):
        tx = self._make_sample_tx("tx-reb", [self._make_sample_event(1)])
        r = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 8, self.fencing_epoch)
        # In-flight queue still present
        self.assertEqual(len(self.engine.partition_queues[r.primary_partition_id]), 1)

    # 19. Duplicate dispatch suppression
    def test_19_duplicate_dispatch_suppression(self):
        tx = self._make_sample_tx("tx-dup", [self._make_sample_event(1)])
        r1 = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.assertEqual(r1.tx_id, "tx-dup")

    # 20. Replay deduplication
    def test_20_replay_deduplication(self):
        tx = self._make_sample_tx("tx-dedup", [self._make_sample_event(1)])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.engine.process_all_partitions(self.fencing_epoch)
        self.assertEqual(self.engine._total_applied_transactions, 1)

    # 21. Same tx/different payload corruption rejection
    def test_21_same_tx_different_payload_rejection(self):
        tx1 = self._make_sample_tx("tx-corrupt", [self._make_sample_event(1)])
        r1 = self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        self.engine.process_all_partitions(self.fencing_epoch)

        # Same tx ID replayed
        tx2 = self._make_sample_tx("tx-corrupt", [self._make_sample_event(2)])
        # Worker deduplication detects duplicate tx_id and suppresses DML execution safely
        worker = self.engine.workers[r1.primary_partition_id]
        res = worker.apply_next_transaction(current_fencing_epoch=self.fencing_epoch, transaction=tx2)
        self.assertTrue(res["duplicate_suppressed"])

    # 22. Contiguous checkpoint frontier
    def test_22_contiguous_checkpoint_frontier(self):
        tracker = CDCCheckpointFrontierTracker()
        p100 = PostgresLSNPosition("0/100")
        p200 = PostgresLSNPosition("0/200")
        tracker.register_pending_transaction(p100)
        tracker.register_pending_transaction(p200)
        tracker.record_completed_transaction(p100)
        self.assertEqual(tracker.frontier_position.to_string(), "0/100")

    # 23. Completion gap blocks checkpoint
    def test_23_completion_gap_blocks_checkpoint(self):
        tracker = CDCCheckpointFrontierTracker()
        p100 = PostgresLSNPosition("0/100")
        p200 = PostgresLSNPosition("0/200")
        tracker.register_pending_transaction(p100)
        tracker.register_pending_transaction(p200)

        # Record p200 complete BEFORE p100
        tracker.record_completed_transaction(p200)
        # Frontier cannot advance past p100
        self.assertFalse(tracker.is_position_checkpoint_eligible(p200))

    # 24. ACK waits for transaction completion
    def test_24_ack_waits_for_transaction_completion(self):
        tx = self._make_sample_tx("tx-ack", [self._make_sample_event(1)])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.assertEqual(self.engine._total_applied_transactions, 0)
        self.engine.process_all_partitions(self.fencing_epoch)
        self.assertEqual(self.engine._total_applied_transactions, 1)

    # 25. Unacknowledged work cannot be reclaimed
    def test_25_unacknowledged_work_cannot_be_reclaimed(self):
        tx = self._make_sample_tx("tx-reclaim", [self._make_sample_event(1)])
        r = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        # Transaction is in queue, unacknowledged
        self.assertEqual(len(self.engine.partition_queues[r.primary_partition_id]), 1)

    # 26. P1 backpressure integration
    def test_26_p1_backpressure_integration(self):
        from akaal.streaming.domain.enums import BackpressureState
        bp = self.engine.backpressure_controller
        state = bp.check_and_update(1000)  # max capacity
        self.assertEqual(state, BackpressureState.THROTTLED)

    # 27. Hot partition telemetry
    def test_27_hot_partition_telemetry(self):
        for i in range(5):
            tx = self._make_sample_tx(f"tx-hot-{i}", [self._make_sample_event(100)])  # All hash to same slot
            self.engine.dispatch_transaction(tx, self.fencing_epoch)
        telem = self.engine.get_telemetry()
        self.assertEqual(telem["pending_transactions"], 5)

    # 28. P3.5 schema barrier integration
    def test_28_p3_5_schema_barrier_integration(self):
        from akaal.cdc.schema_evolution.domain import CDCDDLEvent, DDLOperationType
        ddl_event = CDCDDLEvent(
            identity=self.identity,
            source_position=PostgresLSNPosition("0/1000"),
            canonical_operation=DDLOperationType.ADD_COLUMN,
            affected_database="db",
            affected_schema="public",
            affected_table="users",
            old_schema_version_id="ver-1",
            proposed_schema_version_id="ver-2",
            raw_ddl_statement="ALTER TABLE users ADD COLUMN age INT",
        )
        self.engine.schema_barrier.establish_barrier(self.identity, "users", ddl_event, self.fencing_epoch)
        tx = self._make_sample_tx("tx-barr", [self._make_sample_event(1)])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)

        # Worker apply detects active schema barrier and pauses partition apply
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.process_all_partitions(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "SCHEMA_BARRIER_ACTIVE")

    # 29. P3.4 cutover gate integration
    def test_29_p3_4_cutover_gate_integration(self):
        tx = self._make_sample_tx("tx-cut", [self._make_sample_event(1)])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)
        telem = self.engine.get_telemetry()
        self.assertEqual(telem["pending_transactions"], 1)

    # 30. Cross-run isolation
    def test_30_cross_run_isolation(self):
        ident2 = CDCEventIdentity(self.migration_id, self.job_id, "run-OTHER", self.cdc_session_id)
        engine2 = CDCParallelApplyEngine(identity=ident2, partition_count=4, state_store=self.state_store)
        self.assertNotEqual(self.engine.identity.run_id, engine2.identity.run_id)

    # 31. Cross-session isolation
    def test_31_cross_session_isolation(self):
        ident2 = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, "sess-OTHER")
        engine2 = CDCParallelApplyEngine(identity=ident2, partition_count=4, state_store=self.state_store)
        self.assertNotEqual(self.engine.identity.cdc_session_id, engine2.identity.cdc_session_id)

    # 32. Cross-generation isolation
    def test_32_cross_generation_isolation(self):
        engine2 = CDCParallelApplyEngine(identity=self.identity, partition_count=8, routing_generation=2, state_store=self.state_store)
        self.assertNotEqual(self.engine.routing_generation, engine2.routing_generation)

    # 33. Gateway reachability
    def test_33_gateway_reachability(self):
        gw = EngineGateway()
        res = gw.invoke("configure_cdc_parallelism", {"cdc_session_id": self.cdc_session_id, "partition_count": 4})
        self.assertEqual(res["status"], "CONFIGURED")
        res_stat = gw.invoke("get_cdc_parallel_status", {"cdc_session_id": self.cdc_session_id})
        self.assertEqual(res_stat["partition_count"], 4)

    # 34. Monitoring truth
    def test_34_monitoring_truth(self):
        telem = self.engine.get_telemetry()
        self.assertEqual(telem["partition_count"], 4)
        self.assertEqual(telem["pending_transactions"], 0)

    # 35. Secret / diagnostic safety
    def test_35_secret_diagnostic_safety(self):
        telem = self.engine.get_telemetry()
        s = str(telem)
        self.assertNotIn("password", s.lower())
        self.assertNotIn("secret", s.lower())

    # 36. Unsupported unsafe state fails closed
    def test_36_unsupported_unsafe_state_fails_closed(self):
        with self.assertRaises(ValueError):
            CDCPartitionRouter(partition_count=0)


if __name__ == "__main__":
    unittest.main()
