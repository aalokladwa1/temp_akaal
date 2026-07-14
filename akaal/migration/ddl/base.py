from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from akaal.migration.models import MigrationOperation, DDLCommand, OperationType
from akaal.migration.ddl.utilities.quoting import IdentifierQuoter
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.ddl.utilities.builder import SQLBuilder
from akaal.migration.ddl.utilities.formatter import SQLFormatter
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class BaseDDLGenerator(ABC):
    """
    Abstract Base Class for DDL Translation compilers.
    Coordinates IdentifierQuoters, DialectCapabilities, SQLBuilders,
    and ObjectTranslators to produce structured DDLCommand payloads.
    """
    def __init__(self, quoter: Optional[IdentifierQuoter] = None, capabilities: Optional[DialectCapabilities] = None) -> None:
        self.quoter = quoter or IdentifierQuoter.postgresql()
        self.capabilities = capabilities or DialectCapabilities()
        self.builder = SQLBuilder()
        self.formatter = SQLFormatter()

    @abstractmethod
    def get_dialect_name(self) -> str:
        """Returns the identifier name of this sql dialect."""
        pass

    def generate_commands(self, operations: List[MigrationOperation]) -> List[DDLCommand]:
        """Translates a sequence of migration operations into executable DDLCommands."""
        commands: List[DDLCommand] = []
        for index, op in enumerate(operations):
            cmd = self.generate_command(op, execution_order=index)
            commands.append(cmd)
        return commands

    def generate_command(self, op: MigrationOperation, execution_order: int) -> DDLCommand:
        """Translates a single MigrationOperation into a DDLCommand."""
        obj_type = op.target_object.object_type
        op_type = op.operation_type
        
        # Look up object translator from ObjectTranslatorRegistry
        translator = ObjectTranslatorRegistry.get_translator(obj_type)
        
        # Verify operation type compatibility
        if op_type not in translator.SUPPORTED_OPERATIONS:
            raise ValueError(
                f"Operation type '{op_type}' is not supported by {translator.__class__.__name__} "
                f"for object type '{obj_type}'"
            )

        context = op.context or {}
        
        # Execute translation phase
        if op_type == OperationType.CREATE:
            result = translator.translate_create(
                op.target_object, context, self.quoter, self.capabilities, self.builder
            )
        elif op_type == OperationType.DROP:
            result = translator.translate_drop(
                op.target_object, context, self.quoter, self.capabilities, self.builder
            )
        elif op_type == OperationType.ALTER:
            result = translator.translate_alter(
                op.target_object, context, self.quoter, self.capabilities, self.builder
            )
        else:
            raise ValueError(f"Unsupported operation type: {op_type}")

        sql = result.sql
        rollback_sql = result.rollback_sql
        warnings = list(result.warnings)

        # Apply spacing and trimming formatting
        if sql:
            sql = self.formatter.format(sql)
        if rollback_sql:
            rollback_sql = self.formatter.format(rollback_sql)

        # Delegate dialect overrides hook
        sql, rollback_sql = self._format_dialect_sql(sql, rollback_sql, op)

        return DDLCommand(
            sql=sql,
            rollback_sql=rollback_sql if rollback_sql else None,
            dialect=self.get_dialect_name(),
            execution_order=execution_order,
            transaction_required=self.capabilities.supports_transactional_ddl,
            warnings=tuple(warnings),
            estimated_duration=op.estimated_duration_ms / 1000.0,
            checksum=None,
            metadata=result.metadata
        )

    @abstractmethod
    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        """Dialect-specific SQL formatting adjustments hook."""
        pass
