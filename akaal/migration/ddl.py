from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from akaal.migration.models import MigrationOperation, DDLCommand, OperationType, ObjectType

class BaseDDLGenerator(ABC):
    """
    Abstract Base Class for DDL Generation.
    Defines interface for compiling abstract operations into executable DDLCommand objects.
    """

    @abstractmethod
    def get_dialect_name(self) -> str:
        """Return the dialect name."""
        pass

    def generate_commands(self, operations: List[MigrationOperation]) -> List[DDLCommand]:
        """
        Translates a list of sorted operations into a list of DDLCommand objects.
        """
        commands: List[DDLCommand] = []
        for index, op in enumerate(operations):
            cmd = self.generate_command(op, execution_order=index)
            commands.append(cmd)
        return commands

    def generate_command(self, op: MigrationOperation, execution_order: int) -> DDLCommand:
        """
        Generates a single DDLCommand for the given operation.
        """
        dialect = self.get_dialect_name()
        op_type = op.operation_type
        obj_type = op.target_object.object_type
        name = op.target_object.name
        schema = op.target_object.schema
        schema_prefix = f"{schema}." if schema else ""

        sql = ""
        rollback_sql = ""
        warnings: List[str] = []

        if op_type == OperationType.CREATE:
            if obj_type == ObjectType.TABLE:
                sql = f"CREATE TABLE {schema_prefix}{name} (id INT PRIMARY KEY)"
                rollback_sql = f"DROP TABLE {schema_prefix}{name}"
            elif obj_type == ObjectType.COLUMN:
                parent_table = op.context.get("table_name", "unknown_table")
                data_type = getattr(op.target_object, "data_type", "VARCHAR(255)")
                sql = f"ALTER TABLE {schema_prefix}{parent_table} ADD COLUMN {name} {data_type}"
                rollback_sql = f"ALTER TABLE {schema_prefix}{parent_table} DROP COLUMN {name}"
            elif obj_type == ObjectType.CONSTRAINT:
                parent_table = op.context.get("table_name", "unknown_table")
                c_type = getattr(op.target_object, "constraint_type", "UNIQUE")
                sql = f"ALTER TABLE {schema_prefix}{parent_table} ADD CONSTRAINT {name} {c_type}"
                rollback_sql = f"ALTER TABLE {schema_prefix}{parent_table} DROP CONSTRAINT {name}"
            elif obj_type == ObjectType.INDEX:
                parent_table = op.context.get("table_name", "unknown_table")
                sql = f"CREATE INDEX {name} ON {schema_prefix}{parent_table} (id)"
                rollback_sql = f"DROP INDEX {schema_prefix_index(dialect, schema_prefix, name, parent_table)}"
            elif obj_type == ObjectType.VIEW:
                sql = f"CREATE VIEW {schema_prefix}{name} AS SELECT 1"
                rollback_sql = f"DROP VIEW {schema_prefix}{name}"
            elif obj_type == ObjectType.TRIGGER:
                parent_table = getattr(op.target_object, "table_name", "unknown_table")
                sql = f"CREATE TRIGGER {name} BEFORE INSERT ON {schema_prefix}{parent_table} FOR EACH ROW EXECUTE PROCEDURE test()"
                rollback_sql = f"DROP TRIGGER {name} ON {schema_prefix}{parent_table}"
            else:
                # Fallback for procedures, functions, sequences, partitions, synonyms, materialized views
                sql = f"CREATE {obj_type.value} {schema_prefix}{name}"
                rollback_sql = f"DROP {obj_type.value} {schema_prefix}{name}"

        elif op_type == OperationType.DROP:
            if obj_type == ObjectType.TABLE:
                sql = f"DROP TABLE {schema_prefix}{name}"
                rollback_sql = f"CREATE TABLE {schema_prefix}{name} (id INT PRIMARY KEY)"
                warnings.append(f"Destructive operation: dropping table {name}")
            elif obj_type == ObjectType.COLUMN:
                parent_table = op.context.get("table_name", "unknown_table")
                sql = f"ALTER TABLE {schema_prefix}{parent_table} DROP COLUMN {name}"
                rollback_sql = f"ALTER TABLE {schema_prefix}{parent_table} ADD COLUMN {name} VARCHAR(255)"
                warnings.append(f"Destructive operation: dropping column {name} from {parent_table}")
            elif obj_type == ObjectType.CONSTRAINT:
                parent_table = op.context.get("table_name", "unknown_table")
                sql = f"ALTER TABLE {schema_prefix}{parent_table} DROP CONSTRAINT {name}"
                rollback_sql = f"ALTER TABLE {schema_prefix}{parent_table} ADD CONSTRAINT {name} UNIQUE"
            elif obj_type == ObjectType.INDEX:
                parent_table = op.context.get("table_name", "unknown_table")
                sql = f"DROP INDEX {schema_prefix_index(dialect, schema_prefix, name, parent_table)}"
                rollback_sql = f"CREATE INDEX {name} ON {schema_prefix}{parent_table} (id)"
            else:
                sql = f"DROP {obj_type.value} {schema_prefix}{name}"
                rollback_sql = f"CREATE {obj_type.value} {schema_prefix}{name}"

        elif op_type == OperationType.ALTER:
            if obj_type == ObjectType.COLUMN:
                parent_table = op.context.get("table_name", "unknown_table")
                sql = f"ALTER TABLE {schema_prefix}{parent_table} ALTER COLUMN {name} TYPE VARCHAR(255)"
                rollback_sql = f"ALTER TABLE {schema_prefix}{parent_table} ALTER COLUMN {name} TYPE VARCHAR(100)"
            else:
                sql = f"ALTER {obj_type.value} {schema_prefix}{name}"
                rollback_sql = f"ALTER {obj_type.value} {schema_prefix}{name} BACK"

        # Apply dialect specific SQL modifications
        sql, rollback_sql = self._format_dialect_sql(sql, rollback_sql, op)

        return DDLCommand(
            sql=sql,
            rollback_sql=rollback_sql if rollback_sql else None,
            dialect=dialect,
            execution_order=execution_order,
            transaction_required=True,
            warnings=tuple(warnings),
            estimated_duration=op.estimated_duration_ms / 1000.0,
            metadata={}
        )

    @abstractmethod
    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        """Hook for dialect-specific syntax modifications."""
        pass

def schema_prefix_index(dialect: str, schema_prefix: str, index_name: str, table_name: str) -> str:
    """Helper to format index names for drops based on dialect naming."""
    if dialect == "mysql":
        return f"{index_name} ON {schema_prefix}{table_name}"
    elif dialect == "postgresql":
        return f"{schema_prefix}{index_name}"
    return f"{schema_prefix}{index_name}"


class PostgreSQLDDLGenerator(BaseDDLGenerator):
    """PostgreSQL DDL Generator."""
    def get_dialect_name(self) -> str:
        return "postgresql"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        # PostgreSQL specific syntax defaults
        return sql, rollback_sql


class MySQLDDLGenerator(BaseDDLGenerator):
    """MySQL DDL Generator."""
    def get_dialect_name(self) -> str:
        return "mysql"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        # MySQL uses ADD instead of ADD COLUMN or ALTER COLUMN differently
        if "ADD COLUMN" in sql:
            sql = sql.replace("ADD COLUMN", "ADD")
        if "ALTER COLUMN" in sql:
            sql = sql.replace("ALTER COLUMN", "MODIFY")
        return sql, rollback_sql


class OracleDDLGenerator(BaseDDLGenerator):
    """Oracle DDL Generator."""
    def get_dialect_name(self) -> str:
        return "oracle"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        # Oracle uses ADD (...) instead of ADD COLUMN
        if "ADD COLUMN" in sql:
            sql = sql.replace("ADD COLUMN", "ADD")
        if "ADD CONSTRAINT" in sql and "PRIMARY KEY" in sql:
            # Oracle primary key formatting
            pass
        return sql, rollback_sql


class SQLServerDDLGenerator(BaseDDLGenerator):
    """SQL Server (MSSQL) DDL Generator."""
    def get_dialect_name(self) -> str:
        return "mssql"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        return sql, rollback_sql
