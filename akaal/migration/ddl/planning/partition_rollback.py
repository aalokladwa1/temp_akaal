from typing import Tuple, List, Dict
from akaal.migration.ddl.planning.partition_models import (
    PartitionBaseAction,
    RollbackPlan,
    PlanReadinessStatus,
    CreateChildPartitionAction,
    DetachPartitionAction,
    AttachPartitionAction
)

class PartitionRollbackPlanner:
    @staticmethod
    def plan_rollback(
        forward_actions: Tuple[PartitionBaseAction, ...]
    ) -> RollbackPlan:
        """
        Builds a rollback plan in reverse execution order.
        Converts forward DDL actions to their respective compensating inverse actions.
        """
        rollback_actions: List[PartitionBaseAction] = []

        for action in reversed(forward_actions):
            act_id = f"rollback_{action.action_id}"
            
            # Map forward action to compensating inverse action
            if isinstance(action, CreateChildPartitionAction):
                # Inverse of creating a partition table is dropping it (clean up metadata)
                inverse_action = DetachPartitionAction(
                    action_id=act_id,
                    action_type="DETACH_PARTITION",
                    object_identity=action.object_identity,
                    source_dialect=action.source_dialect,
                    target_dialect=action.target_dialect,
                    child_table_name=action.child_table_name,
                    parent_table_name=action.parent_table_name
                )
            elif isinstance(action, AttachPartitionAction):
                # Inverse of attaching a partition is detaching it
                inverse_action = DetachPartitionAction(
                    action_id=act_id,
                    action_type="DETACH_PARTITION",
                    object_identity=action.object_identity,
                    source_dialect=action.source_dialect,
                    target_dialect=action.target_dialect,
                    child_table_name=action.child_table_name,
                    parent_table_name=action.parent_table_name
                )
            else:
                # Fallback to base action representation
                inverse_action = PartitionBaseAction(
                    action_id=act_id,
                    action_type="COMPENSATING_BASE_ROLLBACK",
                    object_identity=action.object_identity,
                    source_dialect=action.source_dialect,
                    target_dialect=action.target_dialect
                )

            rollback_actions.append(inverse_action)

        return RollbackPlan(
            ordered_actions=tuple(rollback_actions),
            readiness=PlanReadinessStatus.READY
        )
