from typing import List, Dict, Set, Tuple
from akaal.migration.models import MigrationOperation
from akaal.migration.execution.scheduler.models import ScheduledOperation, ExecutionWave, ScheduledPlan
from akaal.migration.execution.scheduler.resource_manager import ResourceManager

class SchedulerPlanner:
    """Computes dependency waves and schedules stages without executing code."""
    def __init__(self, resource_manager: ResourceManager) -> None:
        self.rm = resource_manager

    def build_stages(self, operations: List[MigrationOperation]) -> ScheduledPlan:
        # Group operations by stage metadata
        stages_map: Dict[str, List[MigrationOperation]] = {}
        for op in operations:
            stages_map.setdefault(op.stage, []).append(op)

        # Sort stages deterministically by name
        sorted_stages = sorted(stages_map.keys())
        waves: List[ExecutionWave] = []
        wave_counter = 1
        diagnostics = []

        for stage in sorted_stages:
            stage_ops = stages_map[stage]
            # Map of operation ID -> MigrationOperation
            op_map = {op.operation_id: op for op in stage_ops}
            
            # Keep track of completed operations in this stage
            completed: Set[str] = set()
            remaining = list(stage_ops)

            # Topological waves loop
            while remaining:
                # Find candidate operations whose dependencies are fully resolved
                candidates = []
                for op in remaining:
                    deps_in_stage = [d for d in op.depends_on if d in op_map]
                    if all(d in completed for d in deps_in_stage):
                        candidates.append(op)

                if not candidates:
                    # Circular dependency or missing resolver fallback in stage
                    diagnostics.append(f"Cycle or missing dependency boundary detected in stage '{stage}'")
                    # Force remaining to be resolved to prevent infinite loop
                    for op in remaining:
                        candidates.append(op)

                # Deterministically sort candidates by priority, then operation ID
                candidates.sort(key=lambda o: (o.priority, o.operation_id))

                # Partition candidates into waves respecting ResourceManager limits
                wave_ops: List[ScheduledOperation] = []
                for op in candidates:
                    s_op = ScheduledOperation(
                        operation=op,
                        priority=op.priority,
                        estimated_cost=op.estimated_cost,
                        resource_class=self.rm.evaluate_resource_class(ScheduledOperation(op))
                    )
                    
                    # Test if adding this operation violates wave concurrency limits
                    test_wave = wave_ops + [s_op]
                    if self.rm.verify_wave_concurrency(test_wave) and (op.can_parallelize or not wave_ops):
                        wave_ops.append(s_op)
                        completed.add(op.operation_id)
                        remaining.remove(op)

                if wave_ops:
                    waves.append(ExecutionWave(wave_id=wave_counter, operations=tuple(wave_ops)))
                    wave_counter += 1

        stats = {
            "total_waves": len(waves),
            "total_operations": len(operations),
            "stages_count": len(sorted_stages)
        }

        return ScheduledPlan(waves=tuple(waves), statistics=stats, diagnostics=tuple(diagnostics))
