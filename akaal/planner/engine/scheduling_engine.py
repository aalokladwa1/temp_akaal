"""
Akaal — Scheduling Engine
==========================
Schedules logical resource allocation (CPU, RAM, Workers, Disk, Network, Temp Storage).
Planner performs logical allocation only.
"""

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.resource_schedule import ResourceSchedule, WorkerAllocation
from akaal.planner.models.resource_allocation_graph import ResourceAllocationGraph
from akaal.planner.models.execution_sequence import ExecutionSequence
from akaal.planner.analyzers.resource_analyzer import ResourceAnalyzer


class SchedulingEngine:
    """Performs logical resource scheduling from risk resource estimates and constraints."""

    def build_resource_schedule(
        self, ctx: PlanningContext, sequence: ExecutionSequence
    ) -> tuple:
        analyzer = ResourceAnalyzer()
        resources = analyzer.analyze(ctx)

        recommended_workers = min(
            int(resources.get("recommended_workers", 4)),
            ctx.constraints.max_workers,
        )
        cpu_per_worker = resources.get("recommended_cpu_cores", 4.0) / max(1, recommended_workers)
        mem_per_worker = resources.get("recommended_memory_gb", 8.0) / max(1, recommended_workers)

        alloc_graph = ResourceAllocationGraph()
        workers = []
        task_ids = sequence.ordered_task_ids

        for w in range(recommended_workers):
            worker_id = f"WORKER-{w+1}"
            assigned = task_ids[w::recommended_workers]
            wa = WorkerAllocation(
                worker_id=worker_id,
                assigned_task_ids=assigned,
                allocated_cpu=cpu_per_worker,
                allocated_memory_gb=mem_per_worker,
            )
            workers.append(wa)
            for t_id in assigned:
                alloc_graph.allocate_task(t_id, worker_id, cpu_per_worker, mem_per_worker)

        schedule = ResourceSchedule(
            workers=workers,
            total_cpu_allocated=resources.get("recommended_cpu_cores", 4.0),
            total_memory_allocated_gb=resources.get("recommended_memory_gb", 8.0),
            total_disk_allocated_gb=resources.get("recommended_disk_gb", 50.0),
            network_mbps_allocated=500.0,
        )
        return schedule, alloc_graph
