from akaal.migration.models import MigrationPlan, ObjectType

class TimeEstimator:
    def estimate_time(self, plan: MigrationPlan) -> float:
        if not plan or not plan.operations:
            return 0.0
        # Sum estimated durations in ms
        return sum(getattr(op, "estimated_duration_ms", 100.0) for op in plan.operations)

class StorageEstimator:
    def estimate_storage(self, plan: MigrationPlan) -> int:
        if not plan or not plan.operations:
            return 0
        total_bytes = 0
        for op in plan.operations:
            obj_type = op.target_object.object_type
            if obj_type == ObjectType.TABLE:
                total_bytes += 10 * 1024 * 1024  # 10MB per table
            elif obj_type == ObjectType.COLUMN:
                total_bytes += 1 * 1024 * 1024   # 1MB per column
            elif obj_type == ObjectType.INDEX:
                total_bytes += 2 * 1024 * 1024   # 2MB per index
        return total_bytes

class CostEstimator:
    def estimate_cost(self, plan: MigrationPlan) -> float:
        if not plan or not plan.operations:
            return 0.0
        # Simulated run cost based on operation types
        cost = 0.0
        for op in plan.operations:
            if getattr(op, "destructive", False):
                cost += 5.5
            else:
                cost += 1.2
        return cost
