import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from akaal.migration.ddl.planning.partition_models import (
    PartitionPlan,
    PartitionBaseAction,
    CreatePartitionFunctionAction,
    CreatePartitionSchemeAction,
    CreateChildPartitionAction,
    AttachPartitionAction,
    DetachPartitionAction,
    SplitPartitionAction,
    MergePartitionAction,
    SwitchPartitionAction,
    CaptureCheckpointAction,
    RequireApprovalAction,
    RequireBackupAction,
    RollbackPlan,
    PlanReadinessStatus,
    DowntimeClassification,
    DataMovementClassification,
    ExecutionPolicy
)
from akaal.migration.ddl.planning.partition_scheduler import PartitionDependencyScheduler
from akaal.migration.models.partition import (
    PartitionComparisonReport,
    PartitionCompatibilityReport,
    PartitionDifferenceType,
    PartitionChangeImpact,
    ObjectIdentity
)

class PartitionMigrationPlanner:
    def __init__(self, planner_version: str = "1.0.0"):
        self.planner_version = planner_version

    def plan(
        self,
        comp_report: PartitionComparisonReport,
        compat_report: PartitionCompatibilityReport
    ) -> PartitionPlan:
        """
        Generates a PartitionPlan from difference and compatibility analysis.
        """
        actions: List[PartitionBaseAction] = []
        dep_graph: Dict[str, Tuple[str, ...]] = {}
        lock_graph: Dict[str, Tuple[str, ...]] = {}
        val_graph: Dict[str, Tuple[str, ...]] = {}
        approval_graph: Dict[str, Tuple[str, ...]] = {}
        checkpoint_graph: Dict[str, Tuple[str, ...]] = {}

        # 1. Translate differences to declarative actions
        for idx, diff in enumerate(comp_report.differences):
            act_id = f"act_part_{idx}"
            
            # Map diff type to appropriate action payloads
            if diff.difference_type == PartitionDifferenceType.ADD:
                action = CreateChildPartitionAction(
                    action_id=act_id,
                    action_type="CREATE_CHILD_PARTITION",
                    object_identity=diff.object_identity,
                    source_dialect="postgresql",
                    target_dialect="postgresql",
                    child_table_name=diff.object_identity.name,
                    parent_table_name=diff.object_identity.name.split("_p")[0],
                    boundary=None
                )
            elif diff.difference_type == PartitionDifferenceType.REMOVE:
                action = DetachPartitionAction(
                    action_id=act_id,
                    action_type="DETACH_PARTITION",
                    object_identity=diff.object_identity,
                    source_dialect="postgresql",
                    target_dialect="postgresql",
                    child_table_name=diff.object_identity.name,
                    parent_table_name=diff.object_identity.name.split("_p")[0]
                )
            else:
                action = SplitPartitionAction(
                    action_id=act_id,
                    action_type="SPLIT_PARTITION",
                    object_identity=diff.object_identity,
                    source_dialect="postgresql",
                    target_dialect="postgresql",
                    source_partition=diff.object_identity.name,
                    new_boundaries=(),
                    planner_reason="Range bounds split migration adjustment.",
                    compatibility_decision="NATIVE"
                )

            actions.append(action)
            dep_graph[act_id] = ()
            lock_graph[act_id] = ()
            val_graph[act_id] = ()
            approval_graph[act_id] = ()
            checkpoint_graph[act_id] = ()

        # 2. Schedule actions topologically
        ordered_actions = PartitionDependencyScheduler.schedule(tuple(actions), dep_graph)

        # 3. Compile plan fingerprint
        fp_seed = ":".join(a.action_id for a in ordered_actions)
        plan_fp = hashlib.sha256(f"akaal_v1_partition_planning:{fp_seed}".encode("utf-8")).hexdigest()

        return PartitionPlan(
            plan_id="plan_" + hashlib.sha256(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:8],
            plan_version="1.0.0",
            planner_version=self.planner_version,
            schema_version="1.0.0",
            source_fingerprint=compat_report.source_fingerprint,
            target_fingerprint="",
            policy_fingerprint="",
            ordered_actions=ordered_actions,
            dependency_graph=dep_graph,
            resource_lock_graph=lock_graph,
            validation_graph=val_graph,
            approval_graph=approval_graph,
            checkpoint_graph=checkpoint_graph,
            estimated_downtime=DowntimeClassification.NONE,
            reconstruction_flag=compat_report.reconstruction_required,
            execution_policy=ExecutionPolicy.STOP_ON_FAILURE,
            idempotency_policy="idempotent",
            retry_policy="retry_3_times",
            execution_ordering=tuple(a.action_id for a in ordered_actions),
            planner_metadata={},
            unsupported_capability_list=(),
            warnings=(),
            diagnostics=(),
            readiness=compat_report.overall_readiness,
            plan_fingerprint=plan_fp
        )
