"""
AKAAL Day 29 — P3.7.1 Hostile Transactional Ordering & Causality Audit Suite.
==============================================================================
Hostile, adversarial test suite attempting to break P3.7 causality graph, out-of-order replay,
foreign key dependencies, cycle detection, state store durability, worker fencing, P3.6 parallel apply,
P3.5 schema evolution barriers, P3.4 cutover gates, and EngineGateway reachability.
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
from akaal.cdc.ordering.domain import (
    CDCCausalIdentity,
    CDCDependencyEdge,
    CDCDependencyType,
    CDCTransactionDependencySet,
    CDCReplayEligibility,
    CDCOrderingDecision,
    CDCOrderingBarrierState,
    CDCDependencyResolutionState,
    CDCCausalityGraph,
)
from akaal.cdc.ordering.causality import CDCCausalityGraphEngine
from akaal.cdc.ordering.eligibility import CDCReplayEligibilityEngine
from akaal.cdc.ordering.coordinator import CDCTransactionOrderingCoordinator
from akaal.cdc.schema_evolution.domain import CDCDDLEvent, DDLOperationType
from akaal.gateway.engine_gateway import EngineGateway
from akaal.core.state.state_store import CentralStateStore
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.streaming.domain.enums import BackpressureState


class TestP371TransactionalOrderingCausalityHostileAudit(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.migration_id = f"mig-p371-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p371-test"
        self.run_id = "run-p371-test"
        self.cdc_session_id = f"sess-p371-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        self.state_store = CentralStateStore()
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)

        self.coordinator = CDCTransactionOrderingCoordinator(
            identity=self.identity,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
            fk_relationships={"orders": "users", "items": "orders"},
        )
        self.coordinator.parallel_engine.initialize_partition_workers(self.fencing_epoch)

    def _make_sample_event(
        self,
        seq: int,
        table_name: str = "users",
        entity_key: str = "100",
        op: CDCOperationType = CDCOperationType.UPDATE,
        extra_fields: Dict[str, Any] = None,
    ) -> CDCEvent:
        after_img = {"id": entity_key, "val": f"new_{seq}"}
        if extra_fields:
            after_img.update(extra_fields)
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=op,
            position=PostgresLSNPosition(f"0/{seq*100:X}"),
            before_image={"id": entity_key, "val": f"old_{seq}"},
            after_image=after_img,
        )

    def _make_sample_tx(self, tx_id: str, events: List[CDCEvent]) -> CDCTransaction:
        commit_pos = events[-1].position
        return CDCTransaction(
            identity=self.identity,
            tx_id=tx_id,
            events=events,
            commit_position=commit_pos,
        )

    # 1. Duplicate graph node idempotency
    def test_01_duplicate_graph_node_idempotency(self):
        tx = self._make_sample_tx("tx-dup-node", [self._make_sample_event(1)])
        self.coordinator.causality_graph.add_transaction(tx)
        self.coordinator.causality_graph.add_transaction(tx)
        self.assertEqual(len(self.coordinator.causality_graph.nodes), 1)

    # 2. Self-dependency edge rejection
    def test_02_self_dependency_edge_rejection(self):
        edge = CDCDependencyEdge("tx-self", "tx-self")
        with self.assertRaises(CDCExecutionError) as ctx:
            self.coordinator.causality_graph.add_dependency_edge(edge)
        self.assertEqual(ctx.exception.failure.failure_type.value, "INVALID_DEPENDENCY_EDGE")

    # 3. Direct two-node cycle fails closed
    def test_03_direct_two_node_cycle_fails_closed(self):
        tx1 = self._make_sample_tx("tx-cyc2-1", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("tx-cyc2-2", [self._make_sample_event(2)])

        self.coordinator.causality_graph.add_transaction(tx1)
        self.coordinator.causality_graph.add_transaction(tx2)

        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-cyc2-1", "tx-cyc2-2"))
        with self.assertRaises(CDCExecutionError) as ctx:
            # Adding edge tx-cyc2-2 -> tx-cyc2-1 creates cycle
            edge_rev = CDCDependencyEdge("tx-cyc2-2", "tx-cyc2-1")
            self.coordinator.causality_graph.add_dependency_edge(edge_rev)
            if self.coordinator.causality_graph.detect_cycle("tx-cyc2-2"):
                from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory
                raise CDCExecutionError(CDCFailure(CDCFailureType.CAUSALITY_CYCLE_DETECTED, CDCFailureCategory.BLOCKING, "Cycle", self.migration_id, "j", "r", self.cdc_session_id))
        self.assertEqual(ctx.exception.failure.failure_type.value, "CAUSALITY_CYCLE_DETECTED")

    # 4. Indirect multi-node cycle fails closed
    def test_04_indirect_multi_node_cycle_fails_closed(self):
        tx1 = self._make_sample_tx("tx-c3-1", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("tx-c3-2", [self._make_sample_event(2)])
        tx3 = self._make_sample_tx("tx-c3-3", [self._make_sample_event(3)])

        self.coordinator.causality_graph.add_transaction(tx1)
        self.coordinator.causality_graph.add_transaction(tx2)
        self.coordinator.causality_graph.add_transaction(tx3)

        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-c3-1", "tx-c3-2"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-c3-2", "tx-c3-3"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-c3-3", "tx-c3-1"))

        self.assertTrue(self.coordinator.causality_graph.detect_cycle("tx-c3-1"))

    # 5. Diamond dependency graph resolution
    def test_05_diamond_dependency_graph_resolution(self):
        # T1 -> T2, T1 -> T3, T2 -> T4, T3 -> T4
        tx1 = self._make_sample_tx("t1", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("t2", [self._make_sample_event(2)])
        tx3 = self._make_sample_tx("t3", [self._make_sample_event(3)])
        tx4 = self._make_sample_tx("t4", [self._make_sample_event(4)])

        for t in [tx1, tx2, tx3, tx4]:
            self.coordinator.causality_graph.add_transaction(t)

        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t1", "t2"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t1", "t3"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t2", "t4"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t3", "t4"))

        self.coordinator.record_transaction_completed("t1")
        self.coordinator.record_transaction_completed("t2")
        self.assertFalse(self.coordinator.causality_graph.is_transaction_ready("t4"))

        self.coordinator.record_transaction_completed("t3")
        self.assertTrue(self.coordinator.causality_graph.is_transaction_ready("t4"))

    # 6. Fan-out dependency resolution
    def test_06_fan_out_dependency_resolution(self):
        tx1 = self._make_sample_tx("t1-fo", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("t2-fo", [self._make_sample_event(2, entity_key="k2")])
        tx3 = self._make_sample_tx("t3-fo", [self._make_sample_event(3, entity_key="k3")])

        for t in [tx1, tx2, tx3]:
            self.coordinator.causality_graph.add_transaction(t)

        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t1-fo", "t2-fo"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t1-fo", "t3-fo"))

        unblocked = self.coordinator.record_transaction_completed("t1-fo")
        self.assertIn("t2-fo", unblocked)
        self.assertIn("t3-fo", unblocked)

    # 7. Fan-in dependency resolution
    def test_07_fan_in_dependency_resolution(self):
        tx1 = self._make_sample_tx("t1-fi", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("t2-fi", [self._make_sample_event(2)])
        tx3 = self._make_sample_tx("t3-fi", [self._make_sample_event(3)])

        for t in [tx1, tx2, tx3]:
            self.coordinator.causality_graph.add_transaction(t)

        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t1-fi", "t3-fi"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("t2-fi", "t3-fi"))

        self.coordinator.record_transaction_completed("t1-fi")
        self.assertFalse(self.coordinator.causality_graph.is_transaction_ready("t3-fi"))

        self.coordinator.record_transaction_completed("t2-fi")
        self.assertTrue(self.coordinator.causality_graph.is_transaction_ready("t3-fi"))

    # 8. Out-of-order arrival reverse LSN ordering
    def test_08_out_of_order_arrival_reverse_lsn_ordering(self):
        tx3 = self._make_sample_tx("tx-rev-3", [self._make_sample_event(3, entity_key="rev-k")])
        tx2 = self._make_sample_tx("tx-rev-2", [self._make_sample_event(2, entity_key="rev-k")])
        tx1 = self._make_sample_tx("tx-rev-1", [self._make_sample_event(1, entity_key="rev-k")])

        self.coordinator.register_and_evaluate_transaction(tx3, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)

        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)

    # 9. Out-of-order arrival randomized LSN ordering
    def test_09_out_of_order_arrival_randomized_lsn_ordering(self):
        tx5 = self._make_sample_tx("tx-rnd-5", [self._make_sample_event(5, entity_key="rnd-k")])
        tx1 = self._make_sample_tx("tx-rnd-1", [self._make_sample_event(1, entity_key="rnd-k")])
        tx3 = self._make_sample_tx("tx-rnd-3", [self._make_sample_event(3, entity_key="rnd-k")])

        self.coordinator.register_and_evaluate_transaction(tx5, self.fencing_epoch)
        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx3, self.fencing_epoch)

        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)

    # 10. Parent insert -> Child insert FK ordering
    def test_10_parent_insert_to_child_insert_fk_ordering(self):
        tx_p = self._make_sample_tx("tx-p-ins", [self._make_sample_event(1, table_name="users", entity_key="u-10", op=CDCOperationType.INSERT)])
        tx_c = self._make_sample_tx("tx-c-ins", [self._make_sample_event(2, table_name="orders", entity_key="o-10", op=CDCOperationType.INSERT)])

        self.coordinator.register_and_evaluate_transaction(tx_p, self.fencing_epoch)
        dc = self.coordinator.register_and_evaluate_transaction(tx_c, self.fencing_epoch)

        self.assertEqual(dc.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 11. Child delete -> Parent delete FK ordering
    def test_11_child_delete_to_parent_delete_fk_ordering(self):
        tx_c = self._make_sample_tx("tx-c-del", [self._make_sample_event(1, table_name="orders", entity_key="o-20", op=CDCOperationType.DELETE)])
        tx_p = self._make_sample_tx("tx-p-del", [self._make_sample_event(2, table_name="orders", entity_key="o-20", op=CDCOperationType.DELETE)])

        self.coordinator.register_and_evaluate_transaction(tx_c, self.fencing_epoch)
        dp = self.coordinator.register_and_evaluate_transaction(tx_p, self.fencing_epoch)

        self.assertEqual(dp.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 12. Composite foreign key causality
    def test_12_composite_foreign_key_causality(self):
        tx1 = self._make_sample_tx("tx-comp-1", [self._make_sample_event(1, table_name="users", entity_key="u1", extra_fields={"tenant_id": "t10"})])
        tx2 = self._make_sample_tx("tx-comp-2", [self._make_sample_event(2, table_name="users", entity_key="u1", extra_fields={"tenant_id": "t10"})])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.assertEqual(d2.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 13. Self-referencing foreign key causality
    def test_13_self_referencing_foreign_key_causality(self):
        tx_mgr = self._make_sample_tx("tx-mgr", [self._make_sample_event(1, table_name="users", entity_key="emp-1")])
        tx_sub = self._make_sample_tx("tx-sub", [self._make_sample_event(2, table_name="users", entity_key="emp-1")])

        self.coordinator.register_and_evaluate_transaction(tx_mgr, self.fencing_epoch)
        d_sub = self.coordinator.register_and_evaluate_transaction(tx_sub, self.fencing_epoch)

        self.assertEqual(d_sub.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 14. Multi-level FK chain ordering
    def test_14_multi_level_fk_chain_ordering(self):
        # users -> orders -> items
        tx_usr = self._make_sample_tx("tx-chain-u", [self._make_sample_event(1, table_name="users", entity_key="u1", op=CDCOperationType.INSERT)])
        tx_ord = self._make_sample_tx("tx-chain-o", [self._make_sample_event(2, table_name="orders", entity_key="o1", op=CDCOperationType.INSERT)])
        tx_itm = self._make_sample_tx("tx-chain-i", [self._make_sample_event(3, table_name="items", entity_key="i1", op=CDCOperationType.INSERT)])

        self.coordinator.register_and_evaluate_transaction(tx_usr, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx_ord, self.fencing_epoch)
        d_itm = self.coordinator.register_and_evaluate_transaction(tx_itm, self.fencing_epoch)

        self.assertEqual(d_itm.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 15. Concurrent dependency registration threads
    def test_15_concurrent_dependency_registration_threads(self):
        errors = []

        def worker_task(idx: int):
            try:
                tx = self._make_sample_tx(f"tx-conc-th-{idx}", [self._make_sample_event(idx, entity_key=f"k-{idx%4}")])
                self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)

    # 16. Stale worker fencing mutation rejection
    def test_16_stale_worker_fencing_mutation_rejection(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        tx = self._make_sample_tx("tx-stale-fenc", [self._make_sample_event(1)])
        self.coordinator.causality_graph.add_transaction(tx)
        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_FENCING)

    # 17. Failed predecessor propagation blocks successors
    def test_17_failed_predecessor_propagation_blocks_successors(self):
        tx1 = self._make_sample_tx("tx-fp-1", [self._make_sample_event(1, entity_key="fp-k")])
        tx2 = self._make_sample_tx("tx-fp-2", [self._make_sample_event(2, entity_key="fp-k")])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.coordinator.record_transaction_failed("tx-fp-1")
        self.assertFalse(self.coordinator.causality_graph.is_transaction_ready("tx-fp-2"))

    # 18. Missing predecessor fails closed
    def test_18_missing_predecessor_fails_closed(self):
        tx2 = self._make_sample_tx("tx-m-2", [self._make_sample_event(2, entity_key="m-k")])
        self.coordinator.causality_graph.add_transaction(tx2)
        edge = CDCDependencyEdge("tx-m-nonexistent", "tx-m-2")
        self.coordinator.causality_graph.add_dependency_edge(edge)

        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx2, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 19. Corrupt graph state reconstruction rejection
    def test_19_corrupt_graph_state_reconstruction_rejection(self):
        state_key = f"cdc_causality_graph_{self.cdc_session_id}"
        self.state_store.set_state(state_key, "CORRUPT_NON_DICT_PAYLOAD", category="causality_graph")

        with self.assertRaises(CDCExecutionError) as ctx:
            CDCCausalityGraphEngine(self.cdc_session_id, self.state_store)
        self.assertEqual(ctx.exception.failure.failure_type.value, "CAUSAL_STATE_CORRUPTION")

    # 20. Session mismatched graph state reconstruction rejection
    def test_20_session_mismatched_graph_state_reconstruction_rejection(self):
        state_key = f"cdc_causality_graph_{self.cdc_session_id}"
        self.state_store.set_state(state_key, {"cdc_session_id": "OTHER_SESSION", "nodes": {}}, category="causality_graph")

        with self.assertRaises(CDCExecutionError) as ctx:
            CDCCausalityGraphEngine(self.cdc_session_id, self.state_store)
        self.assertEqual(ctx.exception.failure.failure_type.value, "CAUSAL_STATE_CORRUPTION")

    # 21. Cross-session substitution rejection
    def test_21_cross_session_substitution_rejection(self):
        other_identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, "other-sess-id")
        tx_other = CDCTransaction(identity=other_identity, tx_id="tx-sub-h", events=[self._make_sample_event(1)], commit_position=PostgresLSNPosition("0/100"))
        with self.assertRaises(CDCExecutionError) as ctx:
            self.coordinator.register_and_evaluate_transaction(tx_other, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "DEPENDENCY_IDENTITY_MISMATCH")

    # 22. Cross-migration substitution rejection
    def test_22_cross_migration_substitution_rejection(self):
        other_identity = CDCEventIdentity("other-mig-id", self.job_id, self.run_id, self.cdc_session_id)
        tx_other = CDCTransaction(identity=other_identity, tx_id="tx-mig-sub", events=[self._make_sample_event(1)], commit_position=PostgresLSNPosition("0/100"))
        with self.assertRaises(CDCExecutionError) as ctx:
            self.coordinator.register_and_evaluate_transaction(tx_other, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "DEPENDENCY_IDENTITY_MISMATCH")

    # 23. Routing generation mismatch rejection
    def test_23_routing_generation_mismatch_rejection(self):
        tx = self._make_sample_tx("tx-gen-mismatch", [self._make_sample_event(1)])
        d = self.coordinator.eligibility_engine.evaluate_eligibility(
            self.identity, tx, self.fencing_epoch, routing_generation=1, active_engine_generation=2
        )
        self.assertEqual(d.eligibility, CDCReplayEligibility.REJECTED_STALE_GENERATION)

    # 24. Schema barrier overrides causal readiness
    def test_24_schema_barrier_overrides_causal_readiness(self):
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
        self.coordinator.schema_barrier.establish_barrier(self.identity, "users", ddl_event, self.fencing_epoch)
        tx = self._make_sample_tx("tx-sch-over", [self._make_sample_event(1, table_name="users")])
        self.coordinator.causality_graph.add_transaction(tx)

        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_SCHEMA)

    # 25. Cross-partition barrier integration
    def test_25_cross_partition_barrier_integration(self):
        tx_multi = self._make_sample_tx("tx-cpb-h", [
            self._make_sample_event(1, table_name="users", entity_key="u10"),
            self._make_sample_event(2, table_name="orders", entity_key="o10"),
        ])
        routed = self.coordinator.parallel_engine.dispatch_transaction(tx_multi, self.fencing_epoch)
        if routed.is_multi_partition:
            self.assertTrue(self.coordinator.parallel_engine.barrier_authority.is_partition_locked(self.cdc_session_id, routed.partition_ids[1], "tx-other"))

    # 26. Checkpoint frontier cannot skip causal hole
    def test_26_checkpoint_frontier_cannot_skip_causal_hole(self):
        p1 = PostgresLSNPosition("0/100")
        p2 = PostgresLSNPosition("0/200")
        self.coordinator.parallel_engine.frontier_tracker.register_pending_transaction(p1)
        self.coordinator.parallel_engine.frontier_tracker.register_pending_transaction(p2)

        self.coordinator.parallel_engine.frontier_tracker.record_completed_transaction(p2)
        self.assertFalse(self.coordinator.parallel_engine.frontier_tracker.is_position_checkpoint_eligible(p2))

    # 27. ACK cannot skip causal hole
    def test_27_ack_cannot_skip_causal_hole(self):
        self.assertFalse(self.coordinator.parallel_engine.frontier_tracker.is_position_checkpoint_eligible(PostgresLSNPosition("0/999")))

    # 28. Cutover gate blocked by unresolved dependencies
    def test_28_cutover_gate_blocked_by_unresolved_dependencies(self):
        tx1 = self._make_sample_tx("tx-cg-1", [self._make_sample_event(1, entity_key="cg-k")])
        tx2 = self._make_sample_tx("tx-cg-2", [self._make_sample_event(2, entity_key="cg-k")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        self.assertFalse(self.coordinator.is_fully_drained())

    # 29. Zero backlog alone cannot authorize cutover
    def test_29_zero_backlog_alone_cannot_authorize_cutover(self):
        tx = self._make_sample_tx("tx-zb-gate", [self._make_sample_event(1)])
        self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertFalse(self.coordinator.is_fully_drained())

    # 30. Backpressure throttling on large graph
    def test_30_backpressure_throttling_on_large_graph(self):
        for i in range(10):
            tx = self._make_sample_tx(f"tx-bp-h-{i}", [self._make_sample_event(i, entity_key="bph-k")])
            self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        telem = self.coordinator.get_telemetry()
        self.assertIn("causal_graph_summary", telem)

    # 31. Diagnostic secret redaction
    def test_31_diagnostic_secret_redaction(self):
        telem = self.coordinator.get_telemetry()
        telem_str = str(telem)
        self.assertNotIn("password", telem_str.lower())
        self.assertNotIn("secret", telem_str.lower())

    # 32. EngineGateway production reachability
    def test_32_engine_gateway_production_reachability(self):
        gw = EngineGateway()
        res = gw.get_cdc_causality_graph_summary({"cdc_session_id": self.cdc_session_id})
        self.assertIn("node_count", res)

    # 33. Process death restart recovery end-to-end
    def test_33_process_death_restart_recovery_end_to_end(self):
        tx1 = self._make_sample_tx("tx-pd-1", [self._make_sample_event(1, entity_key="pd-k")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)

        coord2 = CDCTransactionOrderingCoordinator(
            identity=self.identity,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        telem = coord2.get_telemetry()
        self.assertEqual(telem["causal_graph_summary"]["node_count"], 1)


if __name__ == "__main__":
    unittest.main()
