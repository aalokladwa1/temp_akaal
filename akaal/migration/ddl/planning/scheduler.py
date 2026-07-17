"""
Akaal — Dependency Scheduler
=============================
Provides deterministic topological sorting, semantic ordering tie-breakers,
cycle detection, and dependency status propagation for Checkpoint 7.
"""

from typing import Dict, List, Set, Tuple, Optional
from akaal.migration.models import ObjectType
from akaal.migration.ddl.planning.models import (
    DependencyNode,
    DependencyGraph,
    ScheduledIdentityPlan,
    PlanReadinessStatus,
    DependencyStatus,
    ApprovalState,
    ObjectOrigin,
    OperationPhase,
    CycleDiagnostic,
    ObjectIdentity
)

# Semantic ranking dictionaries for ordering keys
PHASE_RANK = {
    OperationPhase.RECONSTRUCT_PRE: 0,
    OperationPhase.DDL_PRE: 1,
    OperationPhase.OBJECT_CREATION: 2,
    OperationPhase.OBJECT_BINDING: 3,
    OperationPhase.DATA_MIGRATION: 4,
    OperationPhase.DDL_POST: 5,
    OperationPhase.VALIDATION: 6,
    OperationPhase.CLEANUP: 7
}

OBJECT_TYPE_RANK = {
    ObjectType.SEQUENCE: 0,
    ObjectType.TABLE: 1,
    ObjectType.COLUMN: 2,
    ObjectType.CONSTRAINT: 3,
    ObjectType.INDEX: 4,
    ObjectType.TRIGGER: 5,
    ObjectType.FUNCTION: 6,
    ObjectType.PROCEDURE: 7,
    ObjectType.VIEW: 8,
    ObjectType.MATERIALIZED_VIEW: 9
}


def calculate_node_ordering_key(node: DependencyNode, identity: Optional[ObjectIdentity]) -> str:
    """
    Computes the deterministic tie-breaking key:
    phase_rank_object_type_rank_schema_name_fingerprint
    """
    phase_val = PHASE_RANK.get(node.operation_phase, 99)
    type_val = 99
    schema_val = ""
    name_val = ""
    
    if identity:
        type_val = OBJECT_TYPE_RANK.get(identity.object_type, 99)
        schema_val = identity.schema
        name_val = identity.name
        
    return f"{phase_val:02d}_{type_val:02d}_{schema_val}_{name_val}_{node.fingerprint_contrib}"


class DependencyScheduler:
    """
    Schedules planned operations topologically.
    Preserves strict tie-breaking determinism and detects cycle paths.
    """

    @staticmethod
    def schedule(graph: DependencyGraph, node_identities: Dict[str, ObjectIdentity]) -> ScheduledIdentityPlan:
        """
        Sorts the DependencyGraph nodes topologically using Kahn's algorithm.
        Breaks ties deterministically using calculation keys.
        """
        # 1. Validation for duplicate nodes
        seen_nodes: Set[str] = set()
        for node in graph.nodes:
            if node.node_id in seen_nodes:
                return ScheduledIdentityPlan(
                    ordered_nodes=(),
                    readiness=PlanReadinessStatus.VALIDATION_FAILURE,
                    fingerprint=""
                )
            seen_nodes.add(node.node_id)

        # 2. Build graph maps
        node_map = {node.node_id: node for node in graph.nodes}
        adj = {node.node_id: list(graph.adjacency_list.get(node.node_id, [])) for node in graph.nodes}
        
        # Build in-degrees map and reverse adjacency (parent -> children)
        in_degree = {node.node_id: 0 for node in graph.nodes}
        parent_to_children: Dict[str, List[str]] = {node.node_id: [] for node in graph.nodes}
        
        for parent_id, children in adj.items():
            for child_id in children:
                if child_id in in_degree:
                    in_degree[child_id] += 1
                    parent_to_children[parent_id].append(child_id)

        # 3. Locate roots (in-degree == 0)
        # Sort roots deterministically using the ordering key
        roots = [node_id for node_id, deg in in_degree.items() if deg == 0]
        roots.sort(key=lambda nid: calculate_node_ordering_key(node_map[nid], node_identities.get(nid)))

        ordered_ids: List[str] = []
        
        while roots:
            # Pop the root with the lowest sorting key
            curr = roots.pop(0)
            ordered_ids.append(curr)
            
            # Decrease in-degrees of children
            children = parent_to_children.get(curr, [])
            # Sort children to keep deterministic processing order
            children.sort(key=lambda nid: calculate_node_ordering_key(node_map[nid], node_identities.get(nid)))
            
            for child in children:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    roots.append(child)
            
            # Re-sort roots to maintain tie-breaking order
            roots.sort(key=lambda nid: calculate_node_ordering_key(node_map[nid], node_identities.get(nid)))

        # 4. Check for cycles
        if len(ordered_ids) < len(graph.nodes):
            # Compile cycle diagnostic details
            remaining = [nid for nid, deg in in_degree.items() if deg > 0]
            cycle_nodes = tuple(sorted(remaining))
            cycle_objs = tuple(node_identities[nid] for nid in cycle_nodes if nid in node_identities)
            diag = CycleDiagnostic(cycle_detected=True, participating_node_ids=cycle_nodes, involved_objects=cycle_objs)
            return ScheduledIdentityPlan(
                ordered_nodes=(),
                readiness=PlanReadinessStatus.CYCLIC,
                fingerprint=""
            )

        # 5. Dependency Propagation & Status Aggregation
        final_nodes: List[DependencyNode] = []
        node_status_map: Dict[str, PlanReadinessStatus] = {}
        
        for nid in ordered_ids:
            node = node_map[nid]
            
            # Check prerequisites
            prereqs_blocked = False
            for prereq in node.prerequisites:
                if prereq in node_status_map and node_status_map[prereq] != PlanReadinessStatus.READY:
                    prereqs_blocked = True
                    break
            
            status = node.readiness_status
            if prereqs_blocked:
                # Propagate dependency failure status
                dep_status = DependencyStatus.BLOCKED
                if status == PlanReadinessStatus.READY:
                    status = PlanReadinessStatus.UNRESOLVED_DEPENDENCY
            else:
                dep_status = DependencyStatus.SATISFIED
                
            node_status_map[nid] = status
            
            updated_node = DependencyNode(
                node_id=node.node_id,
                ordering_key=calculate_node_ordering_key(node, node_identities.get(node.node_id)),
                operation_phase=node.operation_phase,
                prerequisites=node.prerequisites,
                readiness_status=status,
                dependency_status=dep_status,
                approval_state=node.approval_state,
                provenance=node.provenance,
                rollback_ref=node.rollback_ref,
                diagnostics=node.diagnostics,
                fingerprint_contrib=node.fingerprint_contrib
            )
            final_nodes.append(updated_node)

        # 6. Determine Plan-Level Readiness based on precedence hierarchy
        readiness = PlanReadinessStatus.READY
        precedence_list = [
            PlanReadinessStatus.BLOCKED_UNSAFE,
            PlanReadinessStatus.VALIDATION_FAILURE,
            PlanReadinessStatus.UNSUPPORTED,
            PlanReadinessStatus.CYCLIC,
            PlanReadinessStatus.UNRESOLVED_DEPENDENCY,
            PlanReadinessStatus.INCOMPLETE_METADATA,
            PlanReadinessStatus.REQUIRES_APPROVAL,
            PlanReadinessStatus.REQUIRES_RECONSTRUCTION,
            PlanReadinessStatus.REQUIRES_FALLBACK,
            PlanReadinessStatus.PREVIEW_ONLY,
            PlanReadinessStatus.READY
        ]
        
        node_statuses = set(node_status_map.values())
        for p_status in precedence_list:
            if p_status in node_statuses:
                readiness = p_status
                break

        # Calculate final fingerprint
        import hashlib
        fp_seed = ":".join(n.node_id + "_" + n.readiness_status.value for n in final_nodes)
        plan_fp = hashlib.sha256(fp_seed.encode("utf-8")).hexdigest()

        return ScheduledIdentityPlan(
            ordered_nodes=tuple(final_nodes),
            readiness=readiness,
            fingerprint=plan_fp
        )
