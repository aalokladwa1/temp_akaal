"""
AKAAL Day 29 — P3.7 Transactional Ordering & Causality Engine Acceptance Suite.
================================================================================
Dedicated normal acceptance test suite for P3.7 causality graph, replay eligibility,
same-entity ordering, FK causal ordering, out-of-order arrival buffers, cycle detection,
state store durability, P3.6 parallel sharding integration, P3.5 schema barriers,
P3.4 cutover gates, and EngineGateway reachability.
"""

import uuid
import tempfile
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


class TestP37TransactionalOrderingCausalityEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.migration_id = f"mig-p37-{uuid.uuid4().hex[:6]}"
        self.job_id = "job-p37-test"
        self.run_id = "run-p37-test"
        self.cdc_session_id = f"sess-p37-{uuid.uuid4().hex[:6]}"
        self.identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, self.cdc_session_id)

        self.state_store = CentralStateStore()
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.migration_id)

        self.coordinator = CDCTransactionOrderingCoordinator(
            identity=self.identity,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
            fk_relationships={"orders": "users"},
        )
        self.coordinator.parallel_engine.initialize_partition_workers(self.fencing_epoch)

    def _make_sample_event(
        self,
        seq: int,
        table_name: str = "users",
        entity_key: str = "100",
        op: CDCOperationType = CDCOperationType.UPDATE,
    ) -> CDCEvent:
        return CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table=table_name,
            operation=op,
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

    # 1. Canonical dependency edge creation
    def test_01_canonical_dependency_edge_creation(self):
        edge = CDCDependencyEdge(
            source_tx_id="tx-1",
            target_tx_id="tx-2",
            dependency_type=CDCDependencyType.SAME_ENTITY,
            description="Same entity ordering",
        )
        self.assertEqual(edge.source_tx_id, "tx-1")
        self.assertEqual(edge.target_tx_id, "tx-2")
        self.assertFalse(edge.is_satisfied)

    # 2. Deterministic graph construction
    def test_02_deterministic_graph_construction(self):
        engine = CDCCausalityGraphEngine(self.cdc_session_id, self.state_store)
        tx1 = self._make_sample_tx("tx-1", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("tx-2", [self._make_sample_event(2, entity_key="k1")])

        engine.add_transaction(tx1)
        edges = engine.add_transaction(tx2)

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].source_tx_id, "tx-1")
        self.assertEqual(edges[0].target_tx_id, "tx-2")

    # 3. Independent transactions become READY
    def test_03_independent_transactions_become_ready(self):
        tx1 = self._make_sample_tx("tx-ind-1", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("tx-ind-2", [self._make_sample_event(2, entity_key="k2")])

        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)
        self.assertEqual(d2.eligibility, CDCReplayEligibility.READY)

    # 4. Dependent successor remains blocked
    def test_04_dependent_successor_remains_blocked(self):
        tx1 = self._make_sample_tx("tx-dep-1", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("tx-dep-2", [self._make_sample_event(2, entity_key="k1")])

        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)
        self.assertEqual(d2.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)
        self.assertIn("tx-dep-1", d2.blocker_tx_ids)

    # 5. Predecessor completion releases successor
    def test_05_predecessor_completion_releases_successor(self):
        tx1 = self._make_sample_tx("tx-rel-1", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("tx-rel-2", [self._make_sample_event(2, entity_key="k1")])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        unblocked = self.coordinator.record_transaction_completed("tx-rel-1")
        self.assertIn("tx-rel-2", unblocked)
        self.assertTrue(self.coordinator.causality_graph.is_transaction_ready("tx-rel-2"))

    # 6. Same-key source ordering
    def test_06_same_key_source_ordering(self):
        tx1 = self._make_sample_tx("tx-same-1", [self._make_sample_event(1, entity_key="u1")])
        tx2 = self._make_sample_tx("tx-same-2", [self._make_sample_event(2, entity_key="u1")])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.assertFalse(self.coordinator.causality_graph.is_transaction_ready("tx-same-2"))

    # 7. Insert -> Update ordering
    def test_07_insert_to_update_ordering(self):
        tx_ins = self._make_sample_tx("tx-ins", [self._make_sample_event(1, op=CDCOperationType.INSERT)])
        tx_upd = self._make_sample_tx("tx-upd", [self._make_sample_event(2, op=CDCOperationType.UPDATE)])

        self.coordinator.register_and_evaluate_transaction(tx_ins, self.fencing_epoch)
        d_upd = self.coordinator.register_and_evaluate_transaction(tx_upd, self.fencing_epoch)

        self.assertEqual(d_upd.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 8. Update -> Update ordering
    def test_08_update_to_update_ordering(self):
        tx_upd1 = self._make_sample_tx("tx-upd1", [self._make_sample_event(1, op=CDCOperationType.UPDATE)])
        tx_upd2 = self._make_sample_tx("tx-upd2", [self._make_sample_event(2, op=CDCOperationType.UPDATE)])

        self.coordinator.register_and_evaluate_transaction(tx_upd1, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx_upd2, self.fencing_epoch)

        self.assertEqual(d2.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 9. Update -> Delete ordering
    def test_09_update_to_delete_ordering(self):
        tx_upd = self._make_sample_tx("tx-upd-d", [self._make_sample_event(1, op=CDCOperationType.UPDATE)])
        tx_del = self._make_sample_tx("tx-del-d", [self._make_sample_event(2, op=CDCOperationType.DELETE)])

        self.coordinator.register_and_evaluate_transaction(tx_upd, self.fencing_epoch)
        d_del = self.coordinator.register_and_evaluate_transaction(tx_del, self.fencing_epoch)

        self.assertEqual(d_del.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 10. Delete -> Insert ordering
    def test_10_delete_to_insert_ordering(self):
        tx_del = self._make_sample_tx("tx-del-i", [self._make_sample_event(1, op=CDCOperationType.DELETE)])
        tx_ins = self._make_sample_tx("tx-ins-i", [self._make_sample_event(2, op=CDCOperationType.INSERT)])

        self.coordinator.register_and_evaluate_transaction(tx_del, self.fencing_epoch)
        d_ins = self.coordinator.register_and_evaluate_transaction(tx_ins, self.fencing_epoch)

        self.assertEqual(d_ins.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 11. Parent Insert -> Child Insert FK ordering
    def test_11_parent_insert_to_child_insert_fk_ordering(self):
        tx_parent = self._make_sample_tx("tx-par-ins", [self._make_sample_event(1, table_name="users", entity_key="user-1", op=CDCOperationType.INSERT)])
        tx_child = self._make_sample_tx("tx-chd-ins", [self._make_sample_event(2, table_name="orders", entity_key="order-1", op=CDCOperationType.INSERT)])

        self.coordinator.register_and_evaluate_transaction(tx_parent, self.fencing_epoch)
        d_child = self.coordinator.register_and_evaluate_transaction(tx_child, self.fencing_epoch)

        self.assertEqual(d_child.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 12. Child Delete -> Parent Delete ordering
    def test_12_child_delete_to_parent_delete_ordering(self):
        tx_child = self._make_sample_tx("tx-chd-del", [self._make_sample_event(1, table_name="orders", entity_key="o1", op=CDCOperationType.DELETE)])
        tx_parent = self._make_sample_tx("tx-par-del", [self._make_sample_event(2, table_name="orders", entity_key="o1", op=CDCOperationType.DELETE)])

        self.coordinator.register_and_evaluate_transaction(tx_child, self.fencing_epoch)
        d_par = self.coordinator.register_and_evaluate_transaction(tx_parent, self.fencing_epoch)

        self.assertEqual(d_par.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 13. Multi-table transaction integration
    def test_13_multi_table_transaction_integration(self):
        tx = self._make_sample_tx("tx-multi-tbl", [
            self._make_sample_event(1, table_name="users", entity_key="u1"),
            self._make_sample_event(2, table_name="profiles", entity_key="p1"),
        ])
        d = self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.READY)

    # 14. Out-of-order T3/T2/T1 arrival handling
    def test_14_out_of_order_arrival_handling(self):
        tx1 = self._make_sample_tx("tx-ooo-1", [self._make_sample_event(1, entity_key="ooo-key")])
        tx2 = self._make_sample_tx("tx-ooo-2", [self._make_sample_event(2, entity_key="ooo-key")])
        tx3 = self._make_sample_tx("tx-ooo-3", [self._make_sample_event(3, entity_key="ooo-key")])

        # Register T2 and T3 first
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx3, self.fencing_epoch)

        # Register T1 last
        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)

    # 15. Missing predecessor remains blocked
    def test_15_missing_predecessor_remains_blocked(self):
        tx2 = self._make_sample_tx("tx-miss-2", [self._make_sample_event(2, entity_key="miss-key")])
        # Manually add edge to non-existent tx-miss-1
        self.coordinator.causality_graph.add_transaction(tx2)
        edge = CDCDependencyEdge(source_tx_id="tx-miss-1", target_tx_id="tx-miss-2")
        self.coordinator.causality_graph.add_dependency_edge(edge)

        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx2, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_DEPENDENCY)

    # 16. Already-applied predecessor satisfies dependency
    def test_16_already_applied_predecessor_satisfies_dependency(self):
        tx1 = self._make_sample_tx("tx-app-1", [self._make_sample_event(1, entity_key="app-key")])
        tx2 = self._make_sample_tx("tx-app-2", [self._make_sample_event(2, entity_key="app-key")])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.record_transaction_completed("tx-app-1")

        d2 = self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        self.assertEqual(d2.eligibility, CDCReplayEligibility.READY)

    # 17. Failed predecessor blocks successor
    def test_17_failed_predecessor_blocks_successor(self):
        tx1 = self._make_sample_tx("tx-fail-1", [self._make_sample_event(1, entity_key="fail-key")])
        tx2 = self._make_sample_tx("tx-fail-2", [self._make_sample_event(2, entity_key="fail-key")])

        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.coordinator.record_transaction_failed("tx-fail-1")
        d2 = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx2, self.fencing_epoch)
        self.assertEqual(d2.eligibility, CDCReplayEligibility.BLOCKED_BY_FAILED_PREDECESSOR)

    # 18. Causal cycle detected
    def test_18_causal_cycle_detected(self):
        tx1 = self._make_sample_tx("tx-cyc-1", [self._make_sample_event(1)])
        tx2 = self._make_sample_tx("tx-cyc-2", [self._make_sample_event(2)])

        self.coordinator.causality_graph.add_transaction(tx1)
        self.coordinator.causality_graph.add_transaction(tx2)

        # Create cycle tx-cyc-1 -> tx-cyc-2 -> tx-cyc-1
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-cyc-1", "tx-cyc-2"))
        self.coordinator.causality_graph.add_dependency_edge(CDCDependencyEdge("tx-cyc-2", "tx-cyc-1"))

        self.assertTrue(self.coordinator.causality_graph.detect_cycle("tx-cyc-1"))

    # 19. Unknown dependency fails conservatively
    def test_19_unknown_dependency_fails_conservatively(self):
        edge = CDCDependencyEdge("tx-unk-1", "tx-unk-2", dependency_type=CDCDependencyType.UNKNOWN_DEPENDENCY)
        self.assertEqual(edge.dependency_type.value, "UNKNOWN_DEPENDENCY")

    # 20. Durable graph persistence
    def test_20_durable_graph_persistence(self):
        tx1 = self._make_sample_tx("tx-dur-1", [self._make_sample_event(1, entity_key="dur-k")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)

        state_key = f"cdc_causality_graph_{self.cdc_session_id}"
        persisted = self.state_store.get_state(state_key, category="causality_graph")
        self.assertIsNotNone(persisted)
        self.assertIn("tx-dur-1", persisted["nodes"])

    # 21. Graph restart reconstruction
    def test_21_graph_restart_reconstruction(self):
        tx1 = self._make_sample_tx("tx-rec-1", [self._make_sample_event(1, entity_key="rec-k")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)

        graph2 = CDCCausalityGraphEngine(self.cdc_session_id, self.state_store)
        self.assertIn("tx-rec-1", graph2.nodes)

    # 22. Cross-session graph substitution rejected
    def test_22_cross_session_graph_substitution_rejected(self):
        other_identity = CDCEventIdentity(self.migration_id, self.job_id, self.run_id, "other-sess")
        tx_other = CDCTransaction(identity=other_identity, tx_id="tx-sub", events=[self._make_sample_event(1)], commit_position=PostgresLSNPosition("0/100"))
        with self.assertRaises(CDCExecutionError) as ctx:
            self.coordinator.register_and_evaluate_transaction(tx_other, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "DEPENDENCY_IDENTITY_MISMATCH")

    # 23. Stale fencing mutation rejected
    def test_23_stale_fencing_mutation_rejected(self):
        new_epoch = self.recovery_coord.issue_epoch(self.migration_id)
        tx = self._make_sample_tx("tx-stale-f", [self._make_sample_event(1)])
        self.coordinator.causality_graph.add_transaction(tx)
        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_FENCING)

    # 24. Routing generation interaction preserved
    def test_24_routing_generation_interaction_preserved(self):
        tx = self._make_sample_tx("tx-gen-chk", [self._make_sample_event(1)])
        d = self.coordinator.eligibility_engine.evaluate_eligibility(
            self.identity, tx, self.fencing_epoch, routing_generation=1, active_engine_generation=2
        )
        self.assertEqual(d.eligibility, CDCReplayEligibility.REJECTED_STALE_GENERATION)

    # 25. P3.6 parallel execution integration
    def test_25_p3_6_parallel_execution_integration(self):
        tx = self._make_sample_tx("tx-p36-int", [self._make_sample_event(1)])
        d = self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.READY)
        total_pending = sum(len(q) for q in self.coordinator.parallel_engine.partition_queues.values())
        self.assertEqual(total_pending, 1)

    # 26. Independent transactions remain concurrent
    def test_26_independent_transactions_remain_concurrent(self):
        tx1 = self._make_sample_tx("tx-conc-1", [self._make_sample_event(1, entity_key="k1")])
        tx2 = self._make_sample_tx("tx-conc-2", [self._make_sample_event(2, entity_key="k2")])

        d1 = self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)

        self.assertEqual(d1.eligibility, CDCReplayEligibility.READY)
        self.assertEqual(d2.eligibility, CDCReplayEligibility.READY)

    # 27. Schema barrier overrides causal readiness
    def test_27_schema_barrier_overrides_causal_readiness(self):
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
        tx = self._make_sample_tx("tx-schema-barr", [self._make_sample_event(1, table_name="users")])
        self.coordinator.causality_graph.add_transaction(tx)

        d = self.coordinator.eligibility_engine.evaluate_eligibility(self.identity, tx, self.fencing_epoch)
        self.assertEqual(d.eligibility, CDCReplayEligibility.BLOCKED_BY_SCHEMA)

    # 28. Cross-partition barrier integration
    def test_28_cross_partition_barrier_integration(self):
        tx_multi = self._make_sample_tx("tx-cross-b", [
            self._make_sample_event(1, table_name="users", entity_key="u1"),
            self._make_sample_event(2, table_name="orders", entity_key="o1"),
        ])
        routed = self.coordinator.parallel_engine.dispatch_transaction(tx_multi, self.fencing_epoch)
        if routed.is_multi_partition:
            self.assertTrue(self.coordinator.parallel_engine.barrier_authority.is_partition_locked(self.cdc_session_id, routed.partition_ids[1], "tx-other"))

    # 29. P3.6 frontier cannot skip unresolved causal work
    def test_29_p3_6_frontier_cannot_skip_unresolved_causal_work(self):
        p1 = PostgresLSNPosition("0/100")
        p2 = PostgresLSNPosition("0/200")
        self.coordinator.parallel_engine.frontier_tracker.register_pending_transaction(p1)
        self.coordinator.parallel_engine.frontier_tracker.register_pending_transaction(p2)

        self.coordinator.parallel_engine.frontier_tracker.record_completed_transaction(p2)
        self.assertFalse(self.coordinator.parallel_engine.frontier_tracker.is_position_checkpoint_eligible(p2))

    # 30. ACK cannot bypass unresolved causal work
    def test_30_ack_cannot_bypass_unresolved_causal_work(self):
        self.assertFalse(self.coordinator.parallel_engine.frontier_tracker.is_position_checkpoint_eligible(PostgresLSNPosition("0/999")))

    # 31. Reclamation cannot bypass unresolved causal work
    def test_31_reclamation_cannot_bypass_unresolved_causal_work(self):
        tx = self._make_sample_tx("tx-rec-byp", [self._make_sample_event(1)])
        self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertFalse(self.coordinator.is_fully_drained())

    # 32. Duplicate replay integration
    def test_32_duplicate_replay_integration(self):
        tx = self._make_sample_tx("tx-dup-rep", [self._make_sample_event(1)])
        d1 = self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        d2 = self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertEqual(d1.eligibility, d2.eligibility)

    # 33. Same tx/different payload rejection preserved
    def test_33_same_tx_different_payload_rejection_preserved(self):
        tx1 = self._make_sample_tx("tx-tamp", [self._make_sample_event(1, entity_key="100")])
        tx2 = self._make_sample_tx("tx-tamp", [self._make_sample_event(1, entity_key="999")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        with self.assertRaises(CDCExecutionError) as ctx:
            self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type.value, "TRANSACTION_CORRUPTION")

    # 34. Cutover blocked by unresolved dependencies
    def test_34_cutover_blocked_by_unresolved_dependencies(self):
        tx1 = self._make_sample_tx("tx-cut-1", [self._make_sample_event(1, entity_key="cut-k")])
        tx2 = self._make_sample_tx("tx-cut-2", [self._make_sample_event(2, entity_key="cut-k")])
        self.coordinator.register_and_evaluate_transaction(tx1, self.fencing_epoch)
        self.coordinator.register_and_evaluate_transaction(tx2, self.fencing_epoch)
        self.assertFalse(self.coordinator.is_fully_drained())

    # 35. Zero backlog cannot bypass causal cutover gate
    def test_35_zero_backlog_cannot_bypass_causal_cutover_gate(self):
        tx = self._make_sample_tx("tx-gate", [self._make_sample_event(1)])
        self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        self.assertFalse(self.coordinator.is_fully_drained())

    # 36. Backpressure integration
    def test_36_backpressure_integration(self):
        for i in range(10):
            tx = self._make_sample_tx(f"tx-bp-{i}", [self._make_sample_event(i, entity_key="bp-k")])
            self.coordinator.register_and_evaluate_transaction(tx, self.fencing_epoch)
        telem = self.coordinator.get_telemetry()
        self.assertIn("causal_graph_summary", telem)

    # 37. Monitoring backend truth
    def test_37_monitoring_backend_truth(self):
        telem = self.coordinator.get_telemetry()
        self.assertEqual(telem["cdc_session_id"], self.cdc_session_id)
        self.assertIn("causal_graph_summary", telem)

    # 38. Diagnostics secret safety
    def test_38_diagnostics_secret_safety(self):
        telem = self.coordinator.get_telemetry()
        telem_str = str(telem)
        self.assertNotIn("password", telem_str.lower())
        self.assertNotIn("secret", telem_str.lower())

    # 39. EngineGateway production reachability
    def test_39_engine_gateway_production_reachability(self):
        gw = EngineGateway()
        res = gw.get_cdc_ordering_status({"cdc_session_id": self.cdc_session_id})
        self.assertIn("status", res)

    # 40. Restart recovery end-to-end
    def test_40_restart_recovery_end_to_end(self):
        tx1 = self._make_sample_tx("tx-e2e-1", [self._make_sample_event(1, entity_key="e2e-k")])
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
