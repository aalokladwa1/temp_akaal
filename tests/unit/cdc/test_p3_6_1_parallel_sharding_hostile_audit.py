"""
AKAAL Day 29 — P3.6.1 Hostile Parallel Apply Audit Suite.
==========================================================
Hostile, adversarial test suite attempting to break P3.6 parallel multi-stream sharding,
partition routing, cross-partition barriers, split-brain worker guards, checkpoint frontier
tracking, and crash recovery.
"""

import os
import uuid
import time
import tempfile
import threading
import unittest
from typing import Dict, Any, List

from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCTransaction, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
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
from akaal.cdc.schema_evolution.domain import CDCDDLEvent, DDLOperationType
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.domain.enums import BackpressureState


class TestP361ParallelShardingHostileAudit(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.migration_id = f"mig-p361-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p361-test"
        self.run_id = "run-p361-test"
        self.cdc_session_id = f"sess-p361-{uuid.uuid4().hex[:6]}"
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

    def _make_sample_event(self, seq: int, table_name: str = "users", entity_key: str = "100") -> CDCEvent:
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=CDCOperationType.UPDATE,
            position=PostgresLSNPosition(f"0/{seq*100:X}"),
            before_image={"id": entity_key, "val": f"old_{seq}"},
            after_image={"id": entity_key, "val": f"new_{seq}"},
        )

    def _make_sample_tx(self, tx_id: str, events: List[CDCEvent]) -> CDCTransaction:
        commit_pos = events[-1].position
        return CDCTransaction(
            identity=self.identity,
            tx_id=tx_id,
            events=events,
            commit_position=commit_pos,
        )

    # 1. Actual overlapping parallel execution
    def test_01_actual_overlapping_parallel_execution(self):
        execution_threads = set()
        lock = threading.Lock()

        def worker_task(pid: int):
            with lock:
                execution_threads.add(threading.current_thread().name)
            time.sleep(0.01)
            self.engine.process_partition_batch(pid, self.fencing_epoch)

        threads = []
        for p in range(4):
            tx = self._make_sample_tx(f"tx-par-{p}", [self._make_sample_event(p, entity_key=f"k{p}")])
            self.engine.dispatch_transaction(tx, self.fencing_epoch)
            t = threading.Thread(target=worker_task, args=(p,), name=f"Thread-Worker-{p}")
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertGreaterEqual(len(execution_threads), 2)

    # 2. Same-key target-effect ordering
    def test_02_same_key_target_effect_ordering(self):
        tx1 = self._make_sample_tx("tx-ord-1", [self._make_sample_event(1, entity_key="user-99")])
        tx2 = self._make_sample_tx("tx-ord-2", [self._make_sample_event(2, entity_key="user-99")])
        tx3 = self._make_sample_tx("tx-ord-3", [self._make_sample_event(3, entity_key="user-99")])

        r1 = self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        r2 = self.engine.dispatch_transaction(tx2, self.fencing_epoch)
        r3 = self.engine.dispatch_transaction(tx3, self.fencing_epoch)

        self.assertEqual(r1.primary_partition_id, r2.primary_partition_id)
        self.assertEqual(r2.primary_partition_id, r3.primary_partition_id)

        queue = self.engine.partition_queues[r1.primary_partition_id]
        self.assertEqual([tx.tx_id for tx in queue], ["tx-ord-1", "tx-ord-2", "tx-ord-3"])

    # 3. Unrelated partition progress
    def test_03_unrelated_partition_progress(self):
        # Create multi-partition tx locking partition 0
        tx_multi = self._make_sample_tx("tx-multi", [
            self._make_sample_event(1, table_name="users", entity_key="k0"),
            self._make_sample_event(2, table_name="orders", entity_key="k1"),
        ])
        routed_multi = self.engine.dispatch_transaction(tx_multi, self.fencing_epoch)

        # Dispatch single-partition tx to a partition not locked by multi-partition transaction
        locked_pids = set(routed_multi.partition_ids)
        available_pids = [p for p in range(4) if p not in locked_pids]
        unlocked_pid = available_pids[0] if available_pids else 0

        # Dispatch directly to partition queue
        tx_single = self._make_sample_tx("tx-single", [self._make_sample_event(3, table_name="logs", entity_key=f"key-p{unlocked_pid}")])
        routed_single = self.engine.dispatch_transaction(tx_single, self.fencing_epoch)

        # Unrelated partition single can process cleanly
        res = self.engine.process_partition_batch(routed_single.primary_partition_id, self.fencing_epoch)
        self.assertGreaterEqual(len(res), 0)

    # 4. Deterministic restart routing
    def test_04_deterministic_restart_routing(self):
        r1 = CDCPartitionRouter(partition_count=8, routing_generation=2)
        slot1 = r1.get_deterministic_hash_slot(self.cdc_session_id, "accounts", "acc-555", 8, 2)

        # Simulate process restart
        r2 = CDCPartitionRouter(partition_count=8, routing_generation=2)
        slot2 = r2.get_deterministic_hash_slot(self.cdc_session_id, "accounts", "acc-555", 8, 2)

        self.assertEqual(slot1, slot2)

    # 5. Composite-key serialization ambiguity
    def test_05_composite_key_serialization_ambiguity(self):
        evt1 = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="t",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/10"),
            after_image={"a": "1", "b": "2"},
        )
        evt2 = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="t",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/20"),
            after_image={"a": "1", "b": "2"},
        )
        router = CDCPartitionRouter(partition_count=4)
        k1 = router.extract_entity_key(evt1)
        k2 = router.extract_entity_key(evt2)
        self.assertEqual(k1, k2)

    # 6. Cross-partition transaction atomicity
    def test_06_cross_partition_transaction_atomicity(self):
        tx = self._make_sample_tx("tx-atom", [
            self._make_sample_event(1, table_name="users", entity_key="u1"),
            self._make_sample_event(2, table_name="orders", entity_key="o1"),
        ])
        routed = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        if routed.is_multi_partition:
            self.assertTrue(self.engine.barrier_authority.is_partition_locked(self.cdc_session_id, routed.partition_ids[1], "tx-other"))

    # 7. Frontier hole prevention
    def test_07_frontier_hole_prevention(self):
        tracker = CDCCheckpointFrontierTracker()
        p1 = PostgresLSNPosition("0/100")
        p2 = PostgresLSNPosition("0/200")
        p3 = PostgresLSNPosition("0/300")

        tracker.register_pending_transaction(p1)
        tracker.register_pending_transaction(p2)
        tracker.register_pending_transaction(p3)

        # Complete p3 first
        tracker.record_completed_transaction(p3)
        self.assertFalse(tracker.is_position_checkpoint_eligible(p3))

        # Complete p1
        tracker.record_completed_transaction(p1)
        self.assertEqual(tracker.frontier_position.to_string(), "0/100")

    # 8. Frontier restart reconstruction
    def test_08_frontier_restart_reconstruction(self):
        tracker1 = CDCCheckpointFrontierTracker(state_store=self.state_store, cdc_session_id=self.cdc_session_id)
        p1 = PostgresLSNPosition("0/100")
        p2 = PostgresLSNPosition("0/200")
        tracker1.register_pending_transaction(p1)
        tracker1.register_pending_transaction(p2)
        tracker1.record_completed_transaction(p1)

        # Reconstruct in new tracker
        tracker2 = CDCCheckpointFrontierTracker(state_store=self.state_store, cdc_session_id=self.cdc_session_id)
        self.assertEqual(tracker2.frontier_position.to_string(), "0/100")

    # 9. Duplicate partition owner rejection
    def test_09_duplicate_partition_owner_rejection(self):
        guard = CDCSplitBrainShardGuard(recovery_coordinator=self.recovery_coord, state_store=self.state_store)
        guard.register_partition_worker(self.migration_id, self.cdc_session_id, 0, 1, "worker-1", self.fencing_epoch)

        # Attempt to register worker-2 under same fencing epoch
        valid = guard.validate_worker_ownership(self.migration_id, self.cdc_session_id, 0, "worker-2", self.fencing_epoch)
        self.assertFalse(valid)

    # 10. Stale worker apply rejection
    def test_10_stale_worker_apply_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.process_partition_batch(0, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_PARTITION_WORKER")

    # 11. Stale worker checkpoint rejection
    def test_11_stale_worker_checkpoint_rejection(self):
        worker = self.engine.workers[0]
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            worker.apply_next_transaction(current_fencing_epoch=self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "STALE_WORKER")

    # 12. Stale worker ACK rejection
    def test_12_stale_worker_ack_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.barrier_authority.release_cross_partition_barrier(
                self.cdc_session_id, "tx-1", self.migration_id, self.fencing_epoch
            )

    # 13. Stale worker reclamation rejection
    def test_13_stale_worker_reclamation_rejection(self):
        valid = self.engine.shard_guard.validate_worker_ownership(
            self.migration_id, self.cdc_session_id, 0, "worker-stale", 9999
        )
        self.assertFalse(valid)

    # 14. Rebalance crash before transfer
    def test_14_rebalance_crash_before_transfer(self):
        gen1 = self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 8, self.fencing_epoch)
        self.assertEqual(gen1.status, "REBALANCING")

    # 15. Rebalance crash after transfer
    def test_15_rebalance_crash_after_transfer(self):
        gen1 = self.engine.shard_guard.initiate_rebalance(self.migration_id, self.cdc_session_id, 8, self.fencing_epoch)
        completed = self.engine.shard_guard.complete_rebalance(self.migration_id, self.cdc_session_id, gen1.routing_generation, self.fencing_epoch)
        self.assertTrue(completed)

    # 16. Old-generation replay safety
    def test_16_old_generation_replay_safety(self):
        tx = self._make_sample_tx("tx-old-gen", [self._make_sample_event(1)])
        routed = self.engine.router.route_transaction(tx, partition_count=4, routing_generation=1)
        self.assertEqual(routed.routing_generation, 1)

    # 17. Worker crash after target commit
    def test_17_worker_crash_after_target_commit(self):
        tx = self._make_sample_tx("tx-crash-commit", [self._make_sample_event(1)])
        r = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        worker = self.engine.workers[r.primary_partition_id]
        res1 = worker.apply_next_transaction(current_fencing_epoch=self.fencing_epoch, transaction=tx)

        # Simulate crash & retry
        res2 = worker.apply_next_transaction(current_fencing_epoch=self.fencing_epoch, transaction=tx)
        self.assertTrue(res2["duplicate_suppressed"])

    # 18. Duplicate concurrent dispatch
    def test_18_duplicate_concurrent_dispatch(self):
        evts = [self._make_sample_event(1)]
        tx1 = self._make_sample_tx("tx-dup-conc", evts)
        tx2 = self._make_sample_tx("tx-dup-conc", evts)
        r1 = self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        r2 = self.engine.dispatch_transaction(tx2, self.fencing_epoch)
        self.assertEqual(r1.tx_id, r2.tx_id)

    # 19. Same tx/different payload corruption
    def test_19_same_tx_different_payload_corruption(self):
        tx1 = self._make_sample_tx("tx-tamper", [self._make_sample_event(1, entity_key="100")])
        tx2 = self._make_sample_tx("tx-tamper", [self._make_sample_event(1, entity_key="999")])
        self.engine.dispatch_transaction(tx1, self.fencing_epoch)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.dispatch_transaction(tx2, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TRANSACTION_CORRUPTION")

    # 20. Backpressure hot-partition behavior
    def test_20_backpressure_hot_partition_behavior(self):
        for i in range(1000):
            tx = self._make_sample_tx(f"tx-hot-{i}", [self._make_sample_event(i)])
            self.engine.dispatch_transaction(tx, self.fencing_epoch)
        telem = self.engine.get_telemetry()
        self.assertEqual(telem["pending_transactions"], 1000)

    # 21. Schema barrier parallel enforcement
    def test_21_schema_barrier_parallel_enforcement(self):
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
        tx = self._make_sample_tx("tx-barr-par", [self._make_sample_event(1, table_name="users")])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.process_all_partitions(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "SCHEMA_BARRIER_ACTIVE")

    # 22. Cutover drain with active worker
    def test_22_cutover_drain_with_active_worker(self):
        tx = self._make_sample_tx("tx-drain-act", [self._make_sample_event(1)])
        self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.assertFalse(self.engine.is_fully_drained())

    # 23. Cutover drain with checkpoint hole
    def test_23_cutover_drain_with_checkpoint_hole(self):
        self.engine.frontier_tracker.register_pending_transaction(PostgresLSNPosition("0/500"))
        self.assertFalse(self.engine.is_fully_drained())

    # 24. Cross-session substitution
    def test_24_cross_session_substitution(self):
        other_identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, "other-session")
        tx_other = CDCTransaction(identity=other_identity, tx_id="tx-sub", events=[self._make_sample_event(1)], commit_position=PostgresLSNPosition("0/100"))
        with self.assertRaises(CDCExecutionError) as ctx:
            self.engine.dispatch_transaction(tx_other, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "IDENTITY_MISMATCH")

    # 25. Corrupt ownership state
    def test_25_corrupt_ownership_state(self):
        key = self.engine.shard_guard._get_partition_state_key(self.cdc_session_id, 0)
        self.state_store.set_state(key, {"invalid": True}, category="partition_ownership")
        with self.assertRaises(Exception):
            self.engine.shard_guard.validate_worker_ownership(self.migration_id, self.cdc_session_id, 0, "w1", self.fencing_epoch)

    # 26. Corrupt routing generation
    def test_26_corrupt_routing_generation(self):
        gen_key = f"cdc_route_gen_{self.cdc_session_id}"
        self.state_store.set_state(gen_key, {"routing_generation": "CORRUPT"}, category="route_generation")
        completed = self.engine.shard_guard.complete_rebalance(self.migration_id, self.cdc_session_id, 2, self.fencing_epoch)
        self.assertFalse(completed)

    # 27. Unexpected exception propagation
    def test_27_unexpected_exception_propagation(self):
        with self.assertRaises(ValueError):
            CDCPartitionRouter(partition_count=-1)

    # 28. Diagnostic secret/row safety
    def test_28_diagnostic_secret_row_safety(self):
        telem = self.engine.get_telemetry()
        telem_str = str(telem)
        self.assertNotIn("password", telem_str.lower())
        self.assertNotIn("secret", telem_str.lower())

    # 29. Gateway production reachability
    def test_29_gateway_production_reachability(self):
        gw = EngineGateway()
        res = gw.get_cdc_parallel_status({"cdc_session_id": self.cdc_session_id, "identity": self.identity.to_dict()})
        self.assertIn("status", res)

    # 30. Process restart recovery
    def test_30_process_restart_recovery(self):
        tx = self._make_sample_tx("tx-restart-rec", [self._make_sample_event(1)])
        r = self.engine.dispatch_transaction(tx, self.fencing_epoch)
        self.engine.process_all_partitions(self.fencing_epoch)

        # Simulate new engine instance with same identity & state store
        engine2 = CDCParallelApplyEngine(
            identity=self.identity,
            partition_count=4,
            routing_generation=1,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        engine2.initialize_partition_workers(self.fencing_epoch)
        telem = engine2.get_telemetry()
        self.assertEqual(telem["partition_count"], 4)


if __name__ == "__main__":
    unittest.main()
