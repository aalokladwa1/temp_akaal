from typing import List
from akaal.migration.models import OperationType, ObjectType
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_warning, create_error

class DataQualityValidator:
    """Evaluates data quality, integrity rules, and constraint compatibility of migration items."""
    def validate_quality(self, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics: List[ReliabilityDiagnostic] = []
        plan = context.migration_plan
        
        if not plan or not plan.operations:
            return diagnostics

        for op in plan.operations:
            # 1. Nullability Check: Adding NOT NULL columns without default values causes issues
            if op.operation_type == OperationType.CREATE and op.target_object.object_type == ObjectType.COLUMN:
                col = op.target_object
                is_nullable = getattr(col, "nullable", True)
                default_val = getattr(col, "default_value", None)
                if not is_nullable and default_val is None:
                    diagnostics.append(
                        create_error(
                            message=f"Column '{col.name}' is NOT NULL but lacks a default value specification.",
                            category="DATA_QUALITY",
                            recommendation="Add a default value clause or set nullable=True for column creation."
                        )
                    )

            # 2. Referential Check: Validate foreign key constraints
            if op.target_object.object_type == ObjectType.CONSTRAINT:
                constraint = op.target_object
                c_name = constraint.name.lower()
                if "fk" in c_name and "references" not in getattr(constraint, "definition", "").lower():
                    diagnostics.append(
                        create_warning(
                            message=f"Foreign Key constraint '{constraint.name}' definition may lack complete target mappings.",
                            category="INTEGRITY",
                            recommendation="Ensure the foreign key refers explicitly to a unique index or primary key."
                        )
                    )

            # 3. Duplicate checks: dropping unique constraint
            if op.operation_type == OperationType.DROP and op.target_object.object_type == ObjectType.CONSTRAINT:
                constraint = op.target_object
                if "uq" in constraint.name.lower() or "unique" in constraint.name.lower():
                    diagnostics.append(
                        create_warning(
                            message=f"Dropping unique constraint '{constraint.name}' could introduce duplicate row entries.",
                            category="DATA_QUALITY",
                            recommendation="Ensure application-level checks prevent duplicate insertions before dropping constraint."
                        )
                    )

        return diagnostics
