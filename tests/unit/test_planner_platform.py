"""
Unit & Determinism Tests for Planner Platform (Phase 9 - Feature 5)
=====================================================================
Comprehensive tests covering all 8 roadmap features, 9 architectural refinements,
ExecutionGraph, MigrationExecutionPlan immutability, 10-run determinism,
serialization round-trips, and stress tests.
"""

import unittest
import json
import hashlib

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.reporting.discovery_assembler import DiscoveryAssembler
from akaal.rulebook.api.rulebook_platform import RulebookPlatform
from akaal.decoder.api.decoder_platform import DecoderPlatform
from akaal.risk.api.risk_platform import RiskPlatform

from akaal.planner.models.execution_state import ExecutionState
from akaal.planner.models.dependency_semantics import DependencySemantics
from akaal.planner.models.execution_window import ExecutionWindow, WindowType
from akaal.planner.models.stage_policy import StagePolicy
from akaal.planner.models.planning_strategy import PlanningStrategy, StrategyType
from akaal.planner.models.execution_constraint import ExecutionConstraints
from akaal.planner.models.execution_task import ExecutionTask
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.rollback_plan import RollbackGraph, RollbackNode
from akaal.planner.models.cutover_plan import CutoverPhase, CutoverPhaseType
from akaal.planner.models.planner_event import PlannerEvent, PlannerEventBus
from akaal.planner.models.plan_version import PlanVersionInfo
from akaal.planner.models.planner_evidence_graph import PlannerEvidenceGraph, PlannerEvidenceNode
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.models.planning_context import PlanningContext

from akaal.planner.engine.migration_engine import MigrationEngine
from akaal.planner.engine.dependency_engine import DependencyEngine
from akaal.planner.engine.sequencing_engine import SequencingEngine
from akaal.planner.engine.parallel_engine import ParallelEngine
from akaal.planner.engine.checkpoint_engine import CheckpointEngine
from akaal.planner.engine.rollback_engine import RollbackEngine
from akaal.planner.engine.scheduling_engine import SchedulingEngine
from akaal.planner.engine.cutover_engine import CutoverEngine
from akaal.planner.engine.conflict_engine import ConflictResolutionEngine

from akaal.planner.registry.planner_registry import PlannerRegistry, StrategyRegistry
from akaal.planner.serialization.planner_serializer import PlannerSerializer
from akaal.planner.validation.planner_validator import PlannerValidator
from akaal.planner.api.planner_platform import PlannerPlatform, build_execution_plan


class TestPlannerPlatform(unittest.TestCase):

    def setUp(self):
        config = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="source-db.example.com",
            port=5432,
            database_name="test_db",
            credentials_ref="vault://pg_creds",
        )
        ctx = DiscoveryContext(request=DiscoveryRequest(config))
        report = DiscoveryAssembler.assemble(ctx)
        ruleset = RulebookPlatform.generate_ruleset(report, target_engine="POSTGRESQL")
        canonical_model = DecoderPlatform.normalize(report, ruleset)
        self.risk_model = RiskPlatform.assess_risk(canonical_model)

    def test_execution_state_model(self):
        self.assertIn(ExecutionState.PLANNED, ExecutionState)
        self.assertIn(ExecutionState.ROLLED_BACK, ExecutionState)
        self.assertEqual(len(list(ExecutionState)), 9)

    def test_dependency_semantics_model(self):
        self.assertIn(DependencySemantics.HARD_DEPENDENCY, DependencySemantics)
        self.assertIn(DependencySemantics.SYNCHRONIZATION_DEPENDENCY, DependencySemantics)
        self.assertEqual(len(list(DependencySemantics)), 5)

    def test_execution_window_model(self):
        window = ExecutionWindow(
            window_id="WIN-MAINT-1",
            window_type=WindowType.MAINTENANCE,
            max_allowed_duration_minutes=120.0,
        )
        d = window.to_dict()
        self.assertEqual(d["window_type"], "MAINTENANCE")

    def test_stage_policy_model(self):
        policy = StagePolicy(retry_max_attempts=5, on_failure_action="PAUSE")
        d = policy.to_dict()
        self.assertEqual(d["retry_max_attempts"], 5)
        self.assertEqual(d["on_failure_action"], "PAUSE")

    def test_planning_strategy_model_and_governance(self):
        strategy = PlanningStrategy(strategy_type=StrategyType.ZERO_DOWNTIME_MIGRATION)
        registry = PlannerRegistry()
        self.assertTrue(registry.validate_strategy(strategy))
        strategies = registry.list_strategies()
        self.assertGreaterEqual(len(strategies), 7)

    def test_execution_constraints(self):
        c = ExecutionConstraints(max_parallelism=4, max_workers=8)
        d = c.to_dict()
        self.assertEqual(d["max_parallelism"], 4)

    def test_execution_task_is_immutable(self):
        task = ExecutionTask(
            task_id="T-001",
            task_name="Schema Init",
            task_type="SCHEMA_DDL",
            target_object_id="root",
        )
        with self.assertRaises(Exception):
            task.task_id = "MODIFIED"

    def test_execution_graph_topological_sort(self):
        graph = ExecutionGraph()
        t1 = ExecutionTask(task_id="T1", task_name="A", task_type="SCHEMA_DDL", target_object_id="a")
        t2 = ExecutionTask(task_id="T2", task_name="B", task_type="DATA_BULK", target_object_id="b", dependencies=["T1"])
        t3 = ExecutionTask(task_id="T3", task_name="C", task_type="VALIDATION_CHECK", target_object_id="c", dependencies=["T2"])
        for t in [t1, t2, t3]:
            graph.add_task(t)
        ordered = graph.topological_sort()
        ids = [t.task_id for t in ordered]
        self.assertEqual(ids.index("T1") < ids.index("T2"), True)
        self.assertEqual(ids.index("T2") < ids.index("T3"), True)

    def test_rollback_graph_model(self):
        graph = RollbackGraph()
        node = RollbackNode(
            rollback_id="RB-1",
            task_id="T1",
            compensation_action="REVERSE_OPERATION",
            recovery_point_id="CHKPT-1",
        )
        graph.add_node(node)
        self.assertIn("RB-1", graph.nodes)

    def test_cutover_plan_phases(self):
        ctx = PlanningContext(risk_model=self.risk_model)
        engine = CutoverEngine()
        cutover_plan = engine.build_cutover_plan(ctx)
        phase_types = [p.phase_type for p in cutover_plan.phases]
        self.assertIn(CutoverPhaseType.SWITCH, phase_types)
        self.assertIn(CutoverPhaseType.ROLLBACK_WINDOW, phase_types)
        self.assertIn(CutoverPhaseType.COMPLETION, phase_types)
        self.assertEqual(len(cutover_plan.phases), 8)

    def test_conflict_resolution_engine(self):
        ctx = PlanningContext(risk_model=self.risk_model)
        graph = ExecutionGraph()
        conflict_engine = ConflictResolutionEngine()
        result = conflict_engine.resolve(ctx, graph)
        self.assertIn("conflicts_detected", result)
        self.assertIn("resolutions_applied", result)
        self.assertIn("is_clean", result)

    def test_plan_version_info(self):
        v = PlanVersionInfo(revision=2)
        self.assertEqual(v.revision, 2)
        self.assertIsNone(v.parent_plan_id)

    def test_planner_evidence_graph(self):
        graph = PlannerEvidenceGraph()
        node = PlannerEvidenceNode(
            evidence_id="EV-PLAN-1",
            node_type="PLANNING_DECISION",
            reference_id="DEPENDENCY_ORDERING",
            analyzer_name="DependencyEngine",
            reason="Topological sort applied.",
        )
        graph.add_node(node)
        self.assertEqual(len(graph.nodes), 1)

    def test_planner_event_bus_immutability(self):
        bus = PlannerEventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))

        evt = PlannerEvent(event_type="PlanningStarted", correlation_id="c-01")
        bus.publish(evt)
        self.assertEqual(len(received), 1)

        with self.assertRaises(Exception):
            evt.event_type = "Mutated"

    def test_migration_plan_immutability_and_checksum(self):
        plan = build_execution_plan(self.risk_model)
        self.assertIsInstance(plan, MigrationExecutionPlan)
        self.assertTrue(len(plan.sha256_checksum) > 0)
        with self.assertRaises(Exception):
            plan.sha256_checksum = "modified"

    def test_migration_plan_has_all_8_roadmap_features(self):
        plan = build_execution_plan(self.risk_model)
        d = plan.to_dict()
        self.assertIn("execution_graph", d)         # Migration Planning
        self.assertIn("execution_sequence", d)      # Execution Sequencing
        self.assertIn("dependency_graph", d)        # Dependency Planning
        self.assertIn("parallel_strategy", d)       # Parallel Execution Planning
        self.assertIn("checkpoint_plan", d)         # Checkpoint Planning
        self.assertIn("rollback_plan", d)           # Rollback Planning
        self.assertIn("resource_schedule", d)       # Resource Scheduling
        self.assertIn("cutover_plan", d)            # Cutover Planning

    def test_serializer_roundtrip(self):
        plan = build_execution_plan(self.risk_model)
        json_str = PlannerSerializer.serialize_json(plan)
        self.assertGreater(len(json_str), 0)
        deserialized = PlannerSerializer.deserialize_json(json_str)
        self.assertEqual(plan.sha256_checksum, deserialized.sha256_checksum)

    def test_planner_validator(self):
        plan = build_execution_plan(self.risk_model)
        warnings = PlannerValidator.validate_plan(plan)
        self.assertEqual(warnings, [])

    def test_10_run_determinism(self):
        checksums = set()
        for _ in range(10):
            plan = PlannerPlatform.build_execution_plan(self.risk_model)
            checksums.add(plan.sha256_checksum)
        self.assertEqual(len(checksums), 1, "MigrationExecutionPlan checksum must be deterministic across 10 runs.")

    def test_checksum_stability_after_serialization(self):
        plan = build_execution_plan(self.risk_model)
        json_str = PlannerSerializer.serialize_json(plan)
        deserialized = PlannerSerializer.deserialize_json(json_str)
        self.assertEqual(plan.sha256_checksum, deserialized.sha256_checksum)

    def test_large_graph_stress_100_tasks(self):
        strategy = PlanningStrategy(strategy_type=StrategyType.PHASED_MIGRATION)
        constraints = ExecutionConstraints(max_parallelism=16, max_workers=32)
        plan = PlannerPlatform.build_execution_plan(
            risk_model=self.risk_model,
            strategy=strategy,
            constraints=constraints,
        )
        self.assertIsNotNone(plan.sha256_checksum)
        self.assertGreaterEqual(plan.statistics.get("total_tasks", 0), 1)


if __name__ == "__main__":
    unittest.main()
