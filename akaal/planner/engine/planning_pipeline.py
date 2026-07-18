"""
Akaal — Planning Pipeline Orchestrator
=======================================
Orchestrates the complete Planner Platform pipeline sequence.
Calls each single-responsibility engine in deterministic order.
"""

import time
from typing import List, Tuple

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.planning_decision import PlanningDecision
from akaal.planner.models.planner_evidence_graph import PlannerEvidenceGraph, PlannerEvidenceNode
from akaal.planner.models.planning_trace import PlanningTrace, PlanningTraceStep

from akaal.planner.engine.migration_engine import MigrationEngine
from akaal.planner.engine.dependency_engine import DependencyEngine
from akaal.planner.engine.sequencing_engine import SequencingEngine
from akaal.planner.engine.parallel_engine import ParallelEngine
from akaal.planner.engine.checkpoint_engine import CheckpointEngine
from akaal.planner.engine.rollback_engine import RollbackEngine
from akaal.planner.engine.scheduling_engine import SchedulingEngine
from akaal.planner.engine.cutover_engine import CutoverEngine
from akaal.planner.engine.conflict_engine import ConflictResolutionEngine
from akaal.planner.engine.aggregation_engine import AggregationEngine


class PlanningPipeline:
    """Orchestrates the Planner Platform engine pipeline in deterministic sequence."""

    def run(self, ctx: PlanningContext) -> MigrationExecutionPlan:
        t0 = time.time()
        trace = PlanningTrace(correlation_id=ctx.correlation_id)
        decisions: List[PlanningDecision] = []
        evidence_graph = PlannerEvidenceGraph()
        step = 1

        # 1. Generate ExecutionTasks
        t_s = time.time()
        mig_engine = MigrationEngine()
        tasks = mig_engine.generate_tasks(ctx)
        graph = ExecutionGraph()
        for task in tasks:
            graph.add_task(task)
        trace.add_step(PlanningTraceStep(step, "MigrationEngine", "GenerateTasks", duration_ms=(time.time()-t_s)*1000, decisions_made=len(tasks)))
        step += 1

        # 2. Conflict Resolution (before plan assembly)
        t_s = time.time()
        conflict_engine = ConflictResolutionEngine()
        conflict_result = conflict_engine.resolve(ctx, graph)
        trace.add_step(PlanningTraceStep(step, "ConflictResolutionEngine", "ResolveConflicts", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 3. Dependency Analysis
        t_s = time.time()
        dep_engine = DependencyEngine()
        dep_graph = dep_engine.build_dependency_graph(ctx, graph)
        decisions.append(PlanningDecision(decision_type="DEPENDENCY_ORDERING", reason="Topological sort of execution graph."))
        trace.add_step(PlanningTraceStep(step, "DependencyEngine", "BuildDependencyGraph", duration_ms=(time.time()-t_s)*1000, decisions_made=1))
        step += 1

        # 4. Execution Sequencing
        t_s = time.time()
        seq_engine = SequencingEngine()
        sequence = seq_engine.build_sequence(ctx, graph)
        trace.add_step(PlanningTraceStep(step, "SequencingEngine", "BuildSequence", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 5. Parallel Planning
        t_s = time.time()
        par_engine = ParallelEngine()
        parallel_strategy = par_engine.build_parallel_strategy(ctx, graph, sequence)
        decisions.append(PlanningDecision(decision_type="PARALLEL_GROUPING", reason=f"Parallelism capped at {parallel_strategy['safe_parallelism']}."))
        trace.add_step(PlanningTraceStep(step, "ParallelEngine", "BuildParallelStrategy", duration_ms=(time.time()-t_s)*1000, decisions_made=1))
        step += 1

        # 6. Checkpoint Planning
        t_s = time.time()
        chk_engine = CheckpointEngine()
        checkpoint_plan = chk_engine.build_checkpoint_plan(ctx)
        trace.add_step(PlanningTraceStep(step, "CheckpointEngine", "BuildCheckpointPlan", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 7. Rollback Planning
        t_s = time.time()
        roll_engine = RollbackEngine()
        rollback_plan = roll_engine.build_rollback_plan(ctx)
        trace.add_step(PlanningTraceStep(step, "RollbackEngine", "BuildRollbackPlan", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 8. Resource Scheduling
        t_s = time.time()
        sched_engine = SchedulingEngine()
        resource_schedule, alloc_graph = sched_engine.build_resource_schedule(ctx, sequence)
        trace.add_step(PlanningTraceStep(step, "SchedulingEngine", "BuildResourceSchedule", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 9. Cutover Planning
        t_s = time.time()
        cut_engine = CutoverEngine()
        cutover_plan = cut_engine.build_cutover_plan(ctx)
        trace.add_step(PlanningTraceStep(step, "CutoverEngine", "BuildCutoverPlan", duration_ms=(time.time()-t_s)*1000))
        step += 1

        # 10. Assemble Evidence Graph
        for d in decisions:
            evidence_graph.add_node(PlannerEvidenceNode(
                evidence_id=d.decision_id,
                node_type="PLANNING_DECISION",
                reference_id=d.decision_type,
                analyzer_name="PlanningPipeline",
                reason=d.reason,
            ))

        # 11. Aggregation
        trace.total_duration_ms = (time.time() - t0) * 1000

        plan = AggregationEngine.assemble(
            ctx=ctx,
            graph=graph,
            sequence=sequence,
            dep_graph=dep_graph,
            parallel_strategy=parallel_strategy,
            checkpoint_plan=checkpoint_plan,
            rollback_plan=rollback_plan,
            resource_schedule=resource_schedule,
            alloc_graph=alloc_graph,
            cutover_plan=cutover_plan,
            decisions=decisions,
            evidence_graph=evidence_graph,
            trace=trace,
            conflict_result=conflict_result,
        )

        return plan
