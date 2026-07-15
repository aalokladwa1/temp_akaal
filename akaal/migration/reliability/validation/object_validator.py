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

# Register validator instances on registry import
ObjectValidatorRegistry.register(ObjectType.TABLE, TableValidator())
ObjectValidatorRegistry.register(ObjectType.CONSTRAINT, ConstraintValidator())
ObjectValidatorRegistry.register(ObjectType.INDEX, IndexValidator())
ObjectValidatorRegistry.register(ObjectType.VIEW, ViewValidator())
ObjectValidatorRegistry.register(ObjectType.TRIGGER, TriggerValidator())
ObjectValidatorRegistry.register(ObjectType.SEQUENCE, SequenceValidator())
