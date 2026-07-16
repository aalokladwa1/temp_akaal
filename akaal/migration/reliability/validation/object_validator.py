from abc import ABC, abstractmethod
from typing import List
from akaal.migration.models import MigrationObject, ObjectType
from akaal.migration.reliability.context.reliability_context import ReliabilityContext
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.utilities.diagnostics import create_warning, create_error
from akaal.migration.reliability.validation.registry import ObjectValidatorRegistry

class BaseObjectValidator(ABC):
    """Abstract validator contract for database metadata objects."""
    @abstractmethod
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        pass

class TableValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        # Check table name length
        if len(obj.name) > 63:
            diagnostics.append(
                create_warning(
                    message=f"Table name '{obj.name}' exceeds standard 63 characters.",
                    category="VALIDATION",
                    recommendation="Shorten table identifier to preserve cross-db compatibility."
                )
            )
        # Check strict naming rule
        if context.validation_config.strict_naming:
            if not obj.name.islower() and not obj.name.replace("_", "").isalnum():
                diagnostics.append(
                    create_warning(
                        message=f"Table name '{obj.name}' violates strict lowercase snake_case standard.",
                        category="VALIDATION",
                        recommendation="Rename table using only lowercase alphanumeric characters and underscores."
                    )
                )
        return diagnostics

class ConstraintValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        if context.validation_config.strict_naming:
            if not obj.name.startswith(("pk_", "fk_", "uq_", "chk_")):
                diagnostics.append(
                    create_warning(
                        message=f"Constraint '{obj.name}' doesn't match standard prefix pk_/fk_/uq_/chk_.",
                        category="VALIDATION",
                        recommendation="Prefix constraint identifier based on constraint type."
                    )
                )
        return diagnostics

class IndexValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        # Check naming standard
        if context.validation_config.strict_naming:
            if not obj.name.startswith("idx_"):
                diagnostics.append(
                    create_warning(
                        message=f"Index '{obj.name}' does not use standard idx_ prefix.",
                        category="VALIDATION",
                        recommendation="Prefix index name with idx_ prefix."
                    )
                )
        return diagnostics

class ViewValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        if context.validation_config.strict_naming:
            if not obj.name.startswith("v_"):
                diagnostics.append(
                    create_warning(
                        message=f"View '{obj.name}' does not use standard v_ prefix.",
                        category="VALIDATION",
                        recommendation="Prefix view name with v_ prefix."
                    )
                )
        return diagnostics

class TriggerValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        if context.validation_config.strict_naming:
            if not obj.name.startswith("trg_"):
                diagnostics.append(
                    create_warning(
                        message=f"Trigger '{obj.name}' does not use standard trg_ prefix.",
                        category="VALIDATION",
                        recommendation="Prefix trigger name with trg_ prefix."
                    )
                )
        return diagnostics

class SequenceValidator(BaseObjectValidator):
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        if context.validation_config.strict_naming:
            if not obj.name.startswith("seq_"):
                diagnostics.append(
                    create_warning(
                        message=f"Sequence '{obj.name}' does not use standard seq_ prefix.",
                        category="VALIDATION",
                        recommendation="Prefix sequence name with seq_ prefix."
                    )
                )
        return diagnostics

class IdentityCapabilityValidator(BaseObjectValidator):
    """Audits database column identity support configurations against vendor dialect capabilities."""
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        dialect_src = ""
        if context.execution_context:
            dialect_src = context.execution_context.get_metadata("target_dialect") or ""
        if not dialect_src and context.runtime_metadata:
            dialect_src = getattr(context.runtime_metadata, "target_dialect", "") or ""
        target_dialect = str(dialect_src).lower()

        # Gather columns to validate
        columns_to_validate = []
        if obj.object_type == ObjectType.TABLE and hasattr(obj, "columns"):
            columns_to_validate.extend(obj.columns)
        elif obj.object_type == ObjectType.COLUMN:
            columns_to_validate.append(obj)

        for col in columns_to_validate:
            ident = getattr(col, "identity", None)
            if ident:
                if "mssql" in target_dialect and ident.cycle:
                    diagnostics.append(
                        create_warning(
                            message=f"SQL Server identity column '{col.name}' does not support sequence CYCLE behavior.",
                            category="COMPATIBILITY",
                            recommendation="Disable identity cycle parameter."
                        )
                    )
                if "mysql" in target_dialect and ident.start != 1:
                    diagnostics.append(
                        create_warning(
                            message=f"MySQL does not natively support non-default starting sequence values '{ident.start}' on column '{col.name}' without table level overrides.",
                            category="COMPATIBILITY",
                            recommendation="Check table level AUTO_INCREMENT offset."
                        )
                    )
        return diagnostics

class PartitionCapabilityValidator(BaseObjectValidator):
    """Validates partitioning type, boundary checks, and targets support rules."""
    def validate_object(self, obj: MigrationObject, context: ReliabilityContext) -> List[ReliabilityDiagnostic]:
        diagnostics = []
        dialect_src = ""
        if context.execution_context:
            dialect_src = context.execution_context.get_metadata("target_dialect") or ""
        if not dialect_src and context.runtime_metadata:
            dialect_src = getattr(context.runtime_metadata, "target_dialect", "") or ""
        target_dialect = str(dialect_src).lower()
        from akaal.migration.models import PartitionType

        partition_meta = None
        if obj.object_type == ObjectType.TABLE and hasattr(obj, "partition_metadata"):
            partition_meta = obj.partition_metadata

        if partition_meta:
            p_type = partition_meta.partition_type
            if "mssql" in target_dialect and p_type != PartitionType.RANGE:
                diagnostics.append(
                    create_error(
                        message=f"SQL Server only natively supports RANGE partitioning. '{p_type}' is not supported.",
                        category="COMPATIBILITY",
                        recommendation="Convert partition type to RANGE or use custom scheme mappings."
                    )
                )
            if not partition_meta.partition_keys:
                diagnostics.append(
                    create_error(
                        message="Partitioning requires at least one partition key defined.",
                        category="VALIDATION",
                        recommendation="Specify one or more partitioning key columns."
                    )
                )
        return diagnostics

# Register validator instances on registry import
ObjectValidatorRegistry.register(ObjectType.TABLE, TableValidator())
ObjectValidatorRegistry.register(ObjectType.CONSTRAINT, ConstraintValidator())
ObjectValidatorRegistry.register(ObjectType.INDEX, IndexValidator())
ObjectValidatorRegistry.register(ObjectType.VIEW, ViewValidator())
ObjectValidatorRegistry.register(ObjectType.TRIGGER, TriggerValidator())
ObjectValidatorRegistry.register(ObjectType.SEQUENCE, SequenceValidator())
ObjectValidatorRegistry.register(ObjectType.COLUMN, IdentityCapabilityValidator())
ObjectValidatorRegistry.register(ObjectType.PARTITION, PartitionCapabilityValidator())
