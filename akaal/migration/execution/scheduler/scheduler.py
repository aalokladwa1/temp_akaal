from typing import List
from akaal.migration.models import MigrationOperation
from akaal.migration.execution.scheduler.models import ScheduledPlan
from akaal.migration.execution.scheduler.resource_manager import ResourceManager
from akaal.migration.execution.scheduler.planner import SchedulerPlanner

class ParallelScheduler:
    """Public facade managing waves planning and concurrency scheduling logic."""
    def __init__(self, worker_count: int = 4, max_parallel_tables: int = 4) -> None:
        self.rm = ResourceManager(max_workers=worker_count, max_parallel_tables=max_parallel_tables)
        self.planner = SchedulerPlanner(self.rm)

    def generate_schedule(self, operations: List[MigrationOperation]) -> ScheduledPlan:
        """Translates a list of sorted operations into a dependency-safe ScheduledPlan."""
        return self.planner.build_stages(operations)
