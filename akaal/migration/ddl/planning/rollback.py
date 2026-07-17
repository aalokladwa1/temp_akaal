"""
Akaal — Rollback Planner
=========================
Compiles dependency-safe, provenance-aware rollback plans for identity migrations.
"""

from typing import Dict, List, Optional, Tuple
from akaal.migration.ddl.planning.models import (
    RollbackPlan,
    RollbackNode,
    DependencyNode,
    PlanReadinessStatus,
    ObjectOrigin,
    MutationState,
    PriorStateAvailability,
    RollbackClassification
)


class RollbackPlanner:
    """Computes rollback DAGs and verifies object provenance safety."""

    @staticmethod
    def plan_rollback(
        forward_nodes: Tuple[DependencyNode, ...],
        object_origins: Dict[str, ObjectOrigin],
        mutation_states: Dict[str, MutationState],
        prior_state_avail: Dict[str, PriorStateAvailability],
        generator_advanced: bool = False
    ) -> RollbackPlan:
        """
        Creates rollback nodes from planned forward nodes in reverse dependency order.
        Strictly enforces provenance drop-prevention rules.
        """
        rollback_nodes: List[RollbackNode] = []
        
        # Process forward nodes in reverse order
        for node in reversed(forward_nodes):
            node_id = node.node_id
            origin = object_origins.get(node_id, ObjectOrigin.UNKNOWN)
            mutation = mutation_states.get(node_id, MutationState.UNMODIFIED)
            prior_state = prior_state_avail.get(node_id, PriorStateAvailability.ABSENT)
            
            # Provenance Drop-Prevention: Never drop pre-existing objects
            if origin == ObjectOrigin.PRE_EXISTING and mutation == MutationState.DELETED:
                # Dropping a pre-existing object is irreversible unless fully captured
                if prior_state != PriorStateAvailability.CAPTURED:
                    return RollbackPlan(
                        ordered_rollback_nodes=(),
                        readiness=PlanReadinessStatus.BLOCKED_UNSAFE
                    )

            # Reseed rollback logic: check generator advancement
            if generator_advanced and "reseed" in node_id:
                # If target has advanced since plan was generated, exact reseed rollback is impossible
                continue

            # Build rollback node with reverse prerequisites
            prereqs: List[str] = []
            for prereq_id in node.prerequisites:
                prereqs.append(f"rollback_{prereq_id}")
                
            rollback_nodes.append(
                RollbackNode(
                    rollback_node_id=f"rollback_{node_id}",
                    origin_node_id=node_id,
                    revert_command_preview=f"-- ROLLBACK: {node_id}",
                    prerequisites=tuple(prereqs)
                )
            )

        return RollbackPlan(
            ordered_rollback_nodes=tuple(rollback_nodes),
            readiness=PlanReadinessStatus.READY
        )
