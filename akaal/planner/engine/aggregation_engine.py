"""
Akaal — Aggregation Engine
===========================
Merges outputs from all planning engines into immutable MigrationExecutionPlan.
Aggregation is deterministic.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.execution_stage import ExecutionStage
from akaal.planner.models.execution_sequence import ExecutionSequence
from akaal.planner.models.execution_timeline import ExecutionTimeline, TimelineStageEntry
from akaal.planner.models.dependency_graph import PlannerDependencyGraph
from akaal.planner.models.checkpoint_plan import CheckpointPlan
from akaal.planner.models.rollback_plan import RollbackPlan
from akaal.planner.models.resource_schedule import ResourceSchedule
from akaal.planner.models.resource_allocation_graph import ResourceAllocationGraph
from akaal.planner.models.cutover_plan import CutoverPlan
from akaal.planner.models.planning_decision import PlanningDecision
from akaal.planner.models.planner_evidence_graph import PlannerEvidenceGraph
from akaal.planner.models.planning_trace import PlanningTrace
from akaal.planner.models.planner_manifest import PlannerManifest
from akaal.planner.models.plan_version import PlanVersionInfo
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan


class AggregationEngine:
    """Assembles final immutable MigrationExecutionPlan."""

    @staticmethod
    def assemble(
        ctx: PlanningContext,
        graph: ExecutionGraph,
        sequence: ExecutionSequence,
        dep_graph: PlannerDependencyGraph,
        parallel_strategy: Dict[str, Any],
        checkpoint_plan: CheckpointPlan,
        rollback_plan: RollbackPlan,
        resource_schedule: ResourceSchedule,
        alloc_graph: ResourceAllocationGraph,
        cutover_plan: CutoverPlan,
        decisions: List[PlanningDecision],
        evidence_graph: PlannerEvidenceGraph,
        trace: PlanningTrace,
        conflict_result: Dict[str, Any],
    ) -> MigrationExecutionPlan:

        manifest = PlannerManifest(
            risk_model_version=ctx.risk_model.model_version,
            planner_schema_version=ctx.planner_schema_version,
        )
        version_info = PlanVersionInfo()

        # Build stages from parallel groups
        stages: List[Dict[str, Any]] = []
        for stage_id, task_ids in parallel_strategy.get("parallel_groups", {}).items():
            stage_tasks = [graph.get_task(t_id).to_dict() for t_id in task_ids if graph.get_task(t_id)]
            stages.append({
                "stage_id": stage_id,
                "tasks": stage_tasks,
            })

        # Build timeline
        timeline = ExecutionTimeline()
        for i, stage_dict in enumerate(stages):
            entry = TimelineStageEntry(
                stage_id=stage_dict["stage_id"],
                stage_name=stage_dict["stage_id"].replace("_", " ").title(),
                estimated_duration_minutes=len(stage_dict["tasks"]) * 1.0 + 5.0,
                has_checkpoint_boundary=True,
            )
            timeline.timeline_stages.append(entry)
        timeline.total_estimated_duration_minutes = sum(
            e.estimated_duration_minutes for e in timeline.timeline_stages
        )

        metadata = {
            "risk_model_checksum": ctx.risk_model.sha256_checksum,
            "correlation_id": ctx.correlation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "strategy": ctx.strategy.strategy_type.value if hasattr(ctx.strategy.strategy_type, "value") else str(ctx.strategy.strategy_type),
            "conflict_resolution": conflict_result,
        }

        stable = {
            "strategy": ctx.strategy.to_dict(),
            "execution_graph": graph.to_dict(),
            "execution_sequence": sequence.to_dict(),
            "checkpoint_plan": checkpoint_plan.to_dict(),
            "rollback_plan": rollback_plan.to_dict(),
            "cutover_plan": cutover_plan.to_dict(),
        }
        checksum_val = hashlib.sha256(
            json.dumps(stable, default=str, sort_keys=True).encode("utf-8")
        ).hexdigest()
        manifest.model_checksum = checksum_val

        return MigrationExecutionPlan(
            sha256_checksum=checksum_val,
            metadata=metadata,
            manifest=manifest.to_dict(),
            version_info=version_info.to_dict(),
            strategy=ctx.strategy.to_dict(),
            constraints=ctx.constraints.to_dict(),
            execution_graph=graph.to_dict(),
            execution_stages=stages,
            execution_sequence=sequence.to_dict(),
            execution_timeline=timeline.to_dict(),
            dependency_graph=dep_graph.to_dict(),
            parallel_strategy=parallel_strategy,
            checkpoint_plan=checkpoint_plan.to_dict(),
            rollback_plan=rollback_plan.to_dict(),
            resource_schedule=resource_schedule.to_dict(),
            resource_allocation_graph=alloc_graph.to_dict(),
            cutover_plan=cutover_plan.to_dict(),
            planning_decisions=[d.to_dict() for d in decisions],
            evidence_graph=evidence_graph.to_dict(),
            statistics={
                "total_tasks": len(graph.tasks),
                "total_stages": len(stages),
                "total_decisions": len(decisions),
            },
            planning_trace=trace.to_dict(),
        )
