from typing import List, Set
from akaal.migration.execution.scheduler.models import ScheduledOperation

class ResourceManager:
    """Manages worker thresholds, parallel table limits, and resource class boundaries."""
    def __init__(self, max_workers: int = 4, max_parallel_tables: int = 4) -> None:
        self.max_workers = max_workers
        self.max_parallel_tables = max_parallel_tables

    def evaluate_resource_class(self, op: ScheduledOperation) -> str:
        """Determines the resource class weight for scheduling queue sorting."""
        if op.operation.destructive:
            return "EXCLUSIVE"
        if op.operation.requires_lock:
            return "HIGH_LOCK"
        return "DEFAULT"

    def verify_wave_concurrency(self, active_ops: List[ScheduledOperation]) -> bool:
        """Verifies if the concurrent tasks in the wave fit within resource limits."""
        if len(active_ops) > self.max_workers:
            return False

        # Verify parallel table limits and exclusive locking
        locked_tables: Set[str] = set()
        for s_op in active_ops:
            op = s_op.operation
            target = op.target_object
            table = target.attributes.get("table_name") or target.name
            
            if op.requires_lock:
                if table in locked_tables:
                    return False
                locked_tables.add(table)

        return True
