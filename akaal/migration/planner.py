import datetime
from typing import Dict, List, Set, Tuple, Any
from akaal.migration.models import (
    MigrationPlan,
    MigrationOperation,
    SchemaComparisonReport,
    ComparisonDifference,
    OperationType,
    ObjectType,
    Table,
    Column,
    Constraint,
    Index,
    Trigger,
    View,
    MaterializedView,
    Function,
    Procedure,
    Sequence,
    Partition,
    Synonym
)

class SynchronizationPlanner:
    """
    Semantic Planner for database schema migrations.
    Responsible for:
    - Mapping schema differences to abstract operations.
    - Determining execution order dependencies.
    - Asserts concurrency, priority, stage, and lock properties.
    - Versioning the generated plans.
    """

    def __init__(self, planner_version: str = "1.0.0") -> None:
        self.planner_version = planner_version

    def plan(self, report: SchemaComparisonReport) -> MigrationPlan:
        """
        Translates a comparison report to an immutable MigrationPlan.
        """
        operations: List[MigrationOperation] = []

        # Step 1: Create raw operations for all differences
        op_lookup: Dict[str, MigrationOperation] = {}
        
        # Build logical map of creations and drops to identify parent/child nodes
        created_tables: Set[str] = set()
        dropped_tables: Set[str] = set()

        for diff in report.differences:
            if diff.diff_type == "ADD" and diff.object_type == ObjectType.TABLE:
                created_tables.add(diff.object_name)
            elif diff.diff_type == "REMOVE" and diff.object_type == ObjectType.TABLE:
                dropped_tables.add(diff.object_name)

        for diff in report.differences:
            # Determine target object and operation type
            if diff.diff_type == "ADD":
                op_type = OperationType.CREATE
                target_obj = diff.new_object
            elif diff.diff_type == "REMOVE":
                op_type = OperationType.DROP
                target_obj = diff.old_object
            else:
                op_type = OperationType.ALTER
                target_obj = diff.new_object

            if not target_obj:
                continue

            op_id = f"op_{diff.difference_id}"
            
            # Setup stage, priority, locking based on type
            stage = "STAGE_GENERIC"
            priority = 5
            can_parallelize = True
            requires_lock = False
            retryable = True
            destructive = (op_type == OperationType.DROP)
            estimated_cost = 1.0
            estimated_duration_ms = 50.0

            obj_type = diff.object_type
            if obj_type == ObjectType.TABLE:
                stage = "STAGE_TABLES"
                priority = 1
                requires_lock = True
                estimated_cost = 5.0
                estimated_duration_ms = 200.0
            elif obj_type == ObjectType.COLUMN:
                stage = "STAGE_COLUMNS"
                priority = 2
                requires_lock = True
                estimated_cost = 2.0
                estimated_duration_ms = 100.0
            elif obj_type == ObjectType.CONSTRAINT:
                stage = "STAGE_CONSTRAINTS"
                priority = 3
                requires_lock = True
                estimated_cost = 3.0
                estimated_duration_ms = 150.0
            elif obj_type == ObjectType.INDEX:
                stage = "STAGE_INDEXES"
                priority = 4
                can_parallelize = True
                requires_lock = False
                estimated_cost = 4.0
                estimated_duration_ms = 500.0
            elif obj_type in (ObjectType.VIEW, ObjectType.MATERIALIZED_VIEW):
                stage = "STAGE_VIEWS"
                priority = 6
                can_parallelize = True
            elif obj_type in (ObjectType.FUNCTION, ObjectType.PROCEDURE, ObjectType.TRIGGER):
                stage = "STAGE_ROUTINES"
                priority = 7

            # Capture context
            context = {
                "object_key": target_obj.object_key,
                "diff_type": diff.diff_type
            }

            # Extrapolate parent table name for columns/indexes/constraints/triggers/partitions
            parent_table = None
            if hasattr(target_obj, "table_name") and getattr(target_obj, "table_name"):
                parent_table = getattr(target_obj, "table_name")
            elif "table_name" in target_obj.attributes:
                parent_table = target_obj.attributes["table_name"]
            elif "table_name" in target_obj.vendor_metadata:
                parent_table = target_obj.vendor_metadata["table_name"]
            else:
                # Attempt to parse parent table name from logical key (schema.table.column)
                parts = target_obj.object_key.split(".")
                if len(parts) >= 2:
                    parent_table = parts[-2]

            if parent_table:
                context["table_name"] = parent_table

            # Record operation
            op = MigrationOperation(
                operation_id=op_id,
                operation_type=op_type,
                target_object=target_obj,
                depends_on=(),  # will compute in Step 2
                priority=priority,
                stage=stage,
                can_parallelize=can_parallelize,
                requires_lock=requires_lock,
                rollback_operation_id=f"rollback_{op_id}",
                retryable=retryable,
                destructive=destructive,
                estimated_cost=estimated_cost,
                estimated_duration_ms=estimated_duration_ms,
                metadata={},
                context=context
            )
            op_lookup[op_id] = op
            operations.append(op)

        # Step 2: Establish dependencies
        resolved_operations: List[MigrationOperation] = []
        for op in operations:
            depends_on_list: List[str] = []
            target_obj = op.target_object
            parent_table = op.context.get("table_name")

            # Dependency Rules for CREATE (ADD)
            if op.operation_type == OperationType.CREATE:
                # 1. Child object depends on Table creation if parent table is being created
                if parent_table and parent_table in created_tables:
                    # Find table create op_id
                    for other_op in operations:
                        if (other_op.operation_type == OperationType.CREATE 
                                and other_op.target_object.object_type == ObjectType.TABLE 
                                and other_op.target_object.name == parent_table):
                            depends_on_list.append(other_op.operation_id)

                # 2. Foreign Key constraints depend on referenced table creation
                if target_obj.object_type == ObjectType.CONSTRAINT:
                    ref_table = getattr(target_obj, "reference_table", None)
                    if ref_table and ref_table in created_tables:
                        for other_op in operations:
                            if (other_op.operation_type == OperationType.CREATE 
                                    and other_op.target_object.object_type == ObjectType.TABLE 
                                    and other_op.target_object.name == ref_table):
                                depends_on_list.append(other_op.operation_id)

            # Dependency Rules for DROP (REMOVE)
            elif op.operation_type == OperationType.DROP:
                # 1. Table drop depends on child drops (if they are being dropped separately)
                if target_obj.object_type == ObjectType.TABLE:
                    for other_op in operations:
                        if other_op.operation_type == OperationType.DROP:
                            other_parent = other_op.context.get("table_name")
                            if other_parent == target_obj.name and other_op.operation_id != op.operation_id:
                                depends_on_list.append(other_op.operation_id)

                # 2. Referenced Table drop depends on Foreign Key drop
                # If target_obj is a table, and another table has FK pointing to it, T depends on FK drop.
                # Since we don't have full database metadata of referencing tables, if we see any foreign key drop
                # operation pointing to this table in the plan, make table drop depend on it.
                if target_obj.object_type == ObjectType.TABLE:
                    for other_op in operations:
                        if (other_op.operation_type == OperationType.DROP 
                                and other_op.target_object.object_type == ObjectType.CONSTRAINT):
                            ref_table = getattr(other_op.target_object, "reference_table", None)
                            if ref_table == target_obj.name:
                                depends_on_list.append(other_op.operation_id)

            # Re-create frozen MigrationOperation with assigned dependencies
            resolved_op = MigrationOperation(
                operation_id=op.operation_id,
                operation_type=op.operation_type,
                target_object=op.target_object,
                depends_on=tuple(sorted(list(set(depends_on_list)))),
                priority=op.priority,
                stage=op.stage,
                can_parallelize=op.can_parallelize,
                requires_lock=op.requires_lock,
                rollback_operation_id=op.rollback_operation_id,
                retryable=op.retryable,
                destructive=op.destructive,
                estimated_cost=op.estimated_cost,
                estimated_duration_ms=op.estimated_duration_ms,
                metadata=op.metadata,
                context=op.context
            )
            resolved_operations.append(resolved_op)

        # Statistics computation
        statistics = {
            "total_operations": len(resolved_operations),
            "estimated_total_duration_ms": sum(op.estimated_duration_ms for op in resolved_operations),
            "estimated_total_cost": sum(op.estimated_cost for op in resolved_operations),
            "warnings": [],
            "risk_score": 0.0
        }

        # Build MigrationPlan
        plan = MigrationPlan(
            planner_version=self.planner_version,
            plan_version="1.0.0",
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            source_database=report.source_schema,
            target_database=report.target_schema,
            operations=tuple(resolved_operations),
            metadata={},
            statistics=statistics
        )
        return plan
