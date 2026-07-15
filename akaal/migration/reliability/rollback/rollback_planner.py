from typing import List, Tuple
from akaal.migration.models import MigrationPlan, OperationType

class RollbackPlanner:
    """Plans reversed sequences to undo database additions/modifications topologically."""
    def plan_rollback(self, plan: MigrationPlan) -> Tuple[List[str], bool]:
        if not plan or not plan.operations:
            return [], True

        steps: List[str] = []
        safe_to_rollback = True

        # Process in reverse order to handle foreign keys/dependencies safely
        for op in reversed(plan.operations):
            target = op.target_object
            op_type = op.operation_type

            if op_type == OperationType.CREATE:
                steps.append(f"DROP {target.object_type.value} {target.name}")
            elif op_type == OperationType.DROP:
                steps.append(f"CREATE {target.object_type.value} {target.name}")
                # Destructive steps cannot be automatically reversed safely without data loss risk
                if getattr(op, "destructive", False):
                    safe_to_rollback = False
            elif op_type == OperationType.ALTER:
                steps.append(f"REVERT ALTER {target.object_type.value} {target.name}")

        return steps, safe_to_rollback
