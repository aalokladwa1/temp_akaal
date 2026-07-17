"""
Akaal — Table Reconstruction Planner
====================================
Constructs safe, declarative, staged table reconstruction plans for SQL Server and MySQL.
"""

from typing import Dict, List, Optional, Tuple, Any
from akaal.migration.ddl.planning.models import (
    IdentityReconstructionPlan,
    ReconstructionStage,
    ReconstructionStageType,
    PlanReadinessStatus,
    SafetyClassification,
    ApprovalState
)


class SQLServerReconstructionPlanner:
    """Plans full table reconstruction stages for SQL Server."""

    @staticmethod
    def plan_rebuild(
        schema: str,
        table: str,
        column: str,
        column_spec: Dict[str, Any],
        dependent_objects: Dict[str, Any]
    ) -> Tuple[Optional[IdentityReconstructionPlan], PlanReadinessStatus, str]:
        """
        Plans SQL Server table rebuild stages.
        Validates completeness of input metadata.
        """
        # 1. Validate complete column specification evidence
        mandatory_cols = ["data_type", "nullable", "columns_order"]
        for key in mandatory_cols:
            if key not in column_spec or column_spec[key] is None:
                return None, PlanReadinessStatus.INCOMPLETE_METADATA, f"Missing mandatory column metadata: {key}"

        # Temporal tables, sparse columns, collations, and computed columns check
        # If metadata is missing or partial, block with INCOMPLETE_METADATA
        required_deps = ["primary_keys", "foreign_keys", "indexes", "constraints", "triggers", "permissions"]
        for dep in required_deps:
            if dep not in dependent_objects or dependent_objects[dep] is None:
                return None, PlanReadinessStatus.INCOMPLETE_METADATA, f"Missing dependent object category: {dep}"

        # 2. Build declarative stages
        stages = [
            ReconstructionStage(
                stage_id="rebuild_validate",
                stage_type=ReconstructionStageType.VALIDATE_INVENTORY,
                safety_level=SafetyClassification.SAFE
            ),
            ReconstructionStage(
                stage_id="rebuild_backup",
                stage_type=ReconstructionStageType.VERIFY_BACKUP,
                backup_requirement=True
            ),
            ReconstructionStage(
                stage_id="rebuild_shadow",
                stage_type=ReconstructionStageType.PLAN_SHADOW_OBJECT,
                safety_level=SafetyClassification.UNSAFE_REBUILD
            ),
            ReconstructionStage(
                stage_id="rebuild_data_copy",
                stage_type=ReconstructionStageType.PLAN_DATA_COPY,
                safety_level=SafetyClassification.UNSAFE_REBUILD
            ),
            ReconstructionStage(
                stage_id="rebuild_keys",
                stage_type=ReconstructionStageType.VALIDATE_KEYS,
                validation_gates=("key_uniqueness_validation",)
            ),
            ReconstructionStage(
                stage_id="rebuild_swap_approval",
                stage_type=ReconstructionStageType.SWAP_APPROVAL_GATE,
                approval_state=ApprovalState.PENDING
            ),
            ReconstructionStage(
                stage_id="rebuild_swap",
                stage_type=ReconstructionStageType.SWAP_PREVIEW,
                safety_level=SafetyClassification.UNSAFE_REBUILD
            ),
            ReconstructionStage(
                stage_id="rebuild_cleanup",
                stage_type=ReconstructionStageType.CLEANUP_RETAINED_ORIGINAL,
                approval_state=ApprovalState.PENDING
            )
        ]

        plan = IdentityReconstructionPlan(
            reason="Alter column to add/remove IDENTITY property requires rebuild.",
            schema=schema,
            table=table,
            column=column,
            stages=tuple(stages),
            validation_gates=("row_count_validation", "referential_integrity")
        )
        return plan, PlanReadinessStatus.REQUIRES_APPROVAL, "SQL Server table rebuild planned. Approval required."


class MySQLReconstructionPlanner:
    """Plans AUTO_INCREMENT column reconstruction stages for MySQL."""

    @staticmethod
    def plan_rebuild(
        schema: str,
        table: str,
        column: str,
        column_spec: Dict[str, Any],
        indexed: bool = False
    ) -> Tuple[Optional[IdentityReconstructionPlan], PlanReadinessStatus, str]:
        """
        Plans MySQL AUTO_INCREMENT definition updates.
        """
        # 1. Validate complete column attributes
        mandatory_attrs = ["data_type", "nullable", "charset", "collation", "engine"]
        for attr in mandatory_attrs:
            if attr not in column_spec or column_spec[attr] is None:
                return None, PlanReadinessStatus.INCOMPLETE_METADATA, f"Missing MySQL column attribute: {attr}"

        # 2. Key prerequisite check: column must be indexed
        if not indexed:
            return None, PlanReadinessStatus.VALIDATION_FAILURE, "MySQL AUTO_INCREMENT column must be indexed."

        stages = [
            ReconstructionStage(
                stage_id="mysql_validate",
                stage_type=ReconstructionStageType.VALIDATE_INVENTORY,
                safety_level=SafetyClassification.SAFE
            ),
            ReconstructionStage(
                stage_id="mysql_backup",
                stage_type=ReconstructionStageType.VERIFY_BACKUP,
                backup_requirement=True
            ),
            ReconstructionStage(
                stage_id="mysql_alter",
                stage_type=ReconstructionStageType.PLAN_SHADOW_OBJECT,
                safety_level=SafetyClassification.UNSAFE_REBUILD
            ),
            ReconstructionStage(
                stage_id="mysql_reseed",
                stage_type=ReconstructionStageType.RESEED_STAGE,
                safety_level=SafetyClassification.SAFE_RESEED
            )
        ]

        plan = IdentityReconstructionPlan(
            reason="MySQL AUTO_INCREMENT modifications require key verification.",
            schema=schema,
            table=table,
            column=column,
            stages=tuple(stages),
            validation_gates=("key_uniqueness_validation",)
        )
        return plan, PlanReadinessStatus.REQUIRES_APPROVAL, "MySQL AUTO_INCREMENT reconstruction planned. Approval required."
