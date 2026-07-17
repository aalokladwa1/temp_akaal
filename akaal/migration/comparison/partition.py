from typing import List, Tuple, Optional
from akaal.migration.models.partition import (
    CanonicalPartitionScheme,
    PartitionStrategy,
    MetadataConfidence,
    PartitionCompatibilityReport,
    PartitionCapabilityDecision,
    PartitionComparisonReport,
    PartitionDifference,
    PartitionDifferenceType,
    PartitionChangeImpact,
    PlanReadinessStatus,
    DowntimeClassification,
    DataMovementClassification,
    ObjectIdentity
)

class PartitionCompatibilityAnalyzer:
    def analyze(
        self,
        source: CanonicalPartitionScheme,
        target_dialect: str,
        target_version: str
    ) -> PartitionCompatibilityReport:
        """
        Analyzes the compatibility of a source partition scheme with a target database system.
        Maps capability decisions based on the 12 cross-dialect translation matrices.
        """
        decisions: List[PartitionCapabilityDecision] = []
        overall_readiness = PlanReadinessStatus.READY
        reconstruction_required = False

        # Evaluate RANGE/LIST/HASH strategy compatibility
        if source.strategy == PartitionStrategy.HASH:
            # Hash always requires row reconstruction for cross-dialect migrations
            if source.source_dialect != target_dialect:
                reconstruction_required = True
                overall_readiness = PlanReadinessStatus.RECONSTRUCTION_REQUIRED
                decisions.append(
                    PartitionCapabilityDecision(
                        capability="HASH",
                        status="RECONSTRUCTION_REQUIRED",
                        reason="Hash distribution logic differs across RDBMS engines.",
                        evidence=f"Source: {source.source_dialect}, Target: {target_dialect}",
                        required_planner_action="Reconstruct Table",
                        approval_requirement="Administrative Approval Required",
                        rollback_support="Requires backup",
                        downtime_class=DowntimeClassification.EXCLUSIVE_LOCK,
                        data_movement=DataMovementClassification.FULL_TABLE_COPY,
                        blocking=False
                    )
                )
        elif source.strategy == PartitionStrategy.LIST:
            # SQL Server emulation check
            if target_dialect.lower() == "mssql":
                reconstruction_required = True
                overall_readiness = PlanReadinessStatus.RECONSTRUCTION_REQUIRED
                decisions.append(
                    PartitionCapabilityDecision(
                        capability="LIST",
                        status="RECONSTRUCTION_REQUIRED",
                        reason="SQL Server lacks native LIST partitioning; requires check constraint emulation.",
                        evidence="MSSQL target",
                        required_planner_action="Emulate constraints",
                        approval_requirement="Policy approval required",
                        rollback_support="Full rollback",
                        downtime_class=DowntimeClassification.METADATA_LOCK,
                        data_movement=DataMovementClassification.NONE,
                        blocking=False
                    )
                )
            else:
                decisions.append(
                    PartitionCapabilityDecision(
                        capability="LIST",
                        status="NATIVE",
                        reason="Direct equivalent list partitioning supports identical boundary tuples.",
                        evidence="Supported",
                        required_planner_action="None",
                        approval_requirement="None",
                        rollback_support="Full rollback",
                        downtime_class=DowntimeClassification.NONE,
                        data_movement=DataMovementClassification.NONE,
                        blocking=False
                    )
                )
        elif source.strategy == PartitionStrategy.RANGE:
            # PG -> MySQL inclusivity bound shifts
            if source.source_dialect == "postgresql" and target_dialect == "mysql":
                overall_readiness = PlanReadinessStatus.READY_WITH_APPROVAL
                decisions.append(
                    PartitionCapabilityDecision(
                        capability="RANGE",
                        status="LOSSY_APPROVAL_REQUIRED",
                        reason="PostgreSQL inclusive boundaries translated to MySQL LESS THAN exclusive bounds.",
                        evidence="PG -> MySQL range conversion",
                        required_planner_action="Convert boundary successor",
                        approval_requirement="Manual verification recommended",
                        rollback_support="Full rollback",
                        downtime_class=DowntimeClassification.METADATA_LOCK,
                        data_movement=DataMovementClassification.NONE,
                        blocking=False
                    )
                )
            else:
                decisions.append(
                    PartitionCapabilityDecision(
                        capability="RANGE",
                        status="NATIVE",
                        reason="Equivalent range boundaries supported.",
                        evidence="Supported",
                        required_planner_action="None",
                        approval_requirement="None",
                        rollback_support="Full rollback",
                        downtime_class=DowntimeClassification.NONE,
                        data_movement=DataMovementClassification.NONE,
                        blocking=False
                    )
                )

        return PartitionCompatibilityReport(
            source_scheme_fingerprint=source.source_metadata_fingerprint,
            target_dialect=target_dialect,
            target_version=target_version,
            overall_readiness=overall_readiness,
            decisions=tuple(decisions),
            data_compatible=True,
            key_compatible=True,
            boundary_compatible=True,
            storage_compatible=True,
            index_compatible=True,
            constraint_compatible=True,
            reconstruction_required=reconstruction_required
        )

class PartitionComparisonEngine:
    def compare(
        self,
        source: CanonicalPartitionScheme,
        target: CanonicalPartitionScheme
    ) -> PartitionComparisonReport:
        """
        Compares source and target partition schemes to produce deterministic difference reports.
        """
        differences: List[PartitionDifference] = []

        # Compare strategy differences
        if source.strategy != target.strategy:
            differences.append(
                PartitionDifference(
                    difference_id="diff_strategy",
                    difference_type=PartitionDifferenceType.MODIFY,
                    object_identity=source.table_identity,
                    source_value=source.strategy.value,
                    target_value=target.strategy.value,
                    impact=PartitionChangeImpact.RECONSTRUCT_TABLE,
                    data_movement_impact=DataMovementClassification.FULL_TABLE_COPY
                )
            )

        # Map current target partitions name set
        target_parts = {p.partition_name: p for p in target.partitions}

        # Identify missing or modified partitions
        for source_part in source.partitions:
            p_name = source_part.partition_name
            if p_name not in target_parts:
                differences.append(
                    PartitionDifference(
                        difference_id=f"diff_missing_{p_name}",
                        difference_type=PartitionDifferenceType.ADD,
                        object_identity=source_part.object_identity,
                        source_value=p_name,
                        target_value="",
                        impact=PartitionChangeImpact.METADATA_ONLY,
                        data_movement_impact=DataMovementClassification.NONE
                    )
                )
            else:
                target_part = target_parts[p_name]
                if type(source_part) != type(target_part):
                    differences.append(
                        PartitionDifference(
                            difference_id=f"diff_modify_{p_name}",
                            difference_type=PartitionDifferenceType.MODIFY,
                            object_identity=source_part.object_identity,
                            source_value=type(source_part).__name__,
                            target_value=type(target_part).__name__,
                            impact=PartitionChangeImpact.RECONSTRUCT_TABLE,
                            data_movement_impact=DataMovementClassification.FULL_TABLE_COPY
                        )
                    )

        # Identify extra partitions on target
        source_part_names = {p.partition_name for p in source.partitions}
        for p_name, target_part in target_parts.items():
            if p_name not in source_part_names:
                differences.append(
                    PartitionDifference(
                        difference_id=f"diff_extra_{p_name}",
                        difference_type=PartitionDifferenceType.REMOVE,
                        object_identity=target_part.object_identity,
                        source_value="",
                        target_value=p_name,
                        impact=PartitionChangeImpact.METADATA_ONLY,
                        data_movement_impact=DataMovementClassification.NONE
                    )
                )

        return PartitionComparisonReport(differences=tuple(differences))
