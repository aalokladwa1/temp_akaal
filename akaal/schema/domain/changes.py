"""
AKAAL Platform 5 — Strongly Typed Schema Change Model

Provides explicit domain change classes inheriting from BaseSchemaChange.
Every change object exposes validation, dependency analysis, DDL generation, execution, rollback, and audit info.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from akaal.schema.domain.enums import ChangeType, ConstraintType
from akaal.schema.domain.identifiers import OperationID, SchemaIdentifier


@dataclass
class DDLStatement:
    sql: str
    target_object: str
    is_destructive: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyEdge:
    source: str
    target: str
    edge_type: str  # HARD, SOFT, CASCADE


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaseSchemaChange(ABC):
    """Abstract Base Class for all strongly typed schema change objects."""

    def __init__(self, target_object: SchemaIdentifier) -> None:
        self.change_id: str = f"change-{uuid.uuid4().hex[:8]}"
        self.target_object: SchemaIdentifier = target_object

    @property
    @abstractmethod
    def change_type(self) -> ChangeType:
        pass

    @abstractmethod
    def validate(self, schema_context: Any) -> ValidationResult:
        pass

    @abstractmethod
    def analyze_dependencies(self) -> List[DependencyEdge]:
        pass

    @abstractmethod
    def generate_forward_ddl(self) -> List[DDLStatement]:
        pass

    @abstractmethod
    def generate_rollback_ddl(self) -> List[DDLStatement]:
        pass

    def execute(self, executor_ctx: Any) -> bool:
        """Executes forward DDL statements against executor context."""
        statements = self.generate_forward_ddl()
        for stmt in statements:
            if hasattr(executor_ctx, "execute_statement"):
                executor_ctx.execute_statement(stmt.sql)
        return True

    def rollback(self, executor_ctx: Any) -> bool:
        """Executes rollback DDL statements against executor context."""
        statements = self.generate_rollback_ddl()
        for stmt in statements:
            if hasattr(executor_ctx, "execute_statement"):
                executor_ctx.execute_statement(stmt.sql)
        return True

    def audit_info(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "target_object": str(self.target_object),
        }


# --- Table Operations ---

class AddTable(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, columns: List[Dict[str, Any]], primary_key: Optional[List[str]] = None) -> None:
        super().__init__(target_object)
        self.columns = columns
        self.primary_key = primary_key or []

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ADD_TABLE

    def validate(self, schema_context: Any) -> ValidationResult:
        if not self.columns:
            return ValidationResult(is_valid=False, errors=["Table must contain at least one column."])
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        cols_sql = [f"{c['name']} {c['type']}" + (" NOT NULL" if not c.get("nullable", True) else "") for c in self.columns]
        if self.primary_key:
            cols_sql.append(f"PRIMARY KEY ({', '.join(self.primary_key)})")
        sql = f"CREATE TABLE {self.target_object} ({', '.join(cols_sql)});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"DROP TABLE {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object), is_destructive=True)]


class DropTable(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, previous_definition: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(target_object)
        self.previous_definition = previous_definition or {}

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_TABLE

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True, warnings=["Dropping a table results in data loss."])

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"DROP TABLE {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object), is_destructive=True)]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        if not self.previous_definition or "columns" not in self.previous_definition:
            sql = f"-- Rollback placeholder for DROP TABLE {self.target_object}"
        else:
            cols = [f"{c['name']} {c['type']}" for c in self.previous_definition["columns"]]
            sql = f"CREATE TABLE {self.target_object} ({', '.join(cols)});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class RenameTable(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, new_name: str) -> None:
        super().__init__(target_object)
        self.new_name = new_name

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.RENAME_TABLE

    def validate(self, schema_context: Any) -> ValidationResult:
        if not self.new_name:
            return ValidationResult(is_valid=False, errors=["New table name cannot be empty."])
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=str(self.target_object), target=self.new_name, edge_type="SOFT")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} RENAME TO {self.new_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.new_name} RENAME TO {self.target_object.name};"
        return [DDLStatement(sql=sql, target_object=self.new_name)]


# --- Column Operations ---

class AddColumn(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, column_name: str, data_type: str, nullable: bool = True, default_value: Optional[str] = None) -> None:
        super().__init__(target_object)
        self.column_name = column_name
        self.data_type = data_type
        self.nullable = nullable
        self.default_value = default_value

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ADD_COLUMN

    def validate(self, schema_context: Any) -> ValidationResult:
        if not self.nullable and self.default_value is None:
            return ValidationResult(is_valid=False, errors=["NOT NULL column must have a default value."])
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=f"{self.target_object}.{self.column_name}", target=str(self.target_object), edge_type="HARD")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        null_clause = " NULL" if self.nullable else " NOT NULL"
        def_clause = f" DEFAULT {self.default_value}" if self.default_value is not None else ""
        sql = f"ALTER TABLE {self.target_object} ADD COLUMN {self.column_name} {self.data_type}{null_clause}{def_clause};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP COLUMN {self.column_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object), is_destructive=True)]


class DropColumn(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, column_name: str, previous_type: Optional[str] = None) -> None:
        super().__init__(target_object)
        self.column_name = column_name
        self.previous_type = previous_type or "VARCHAR(255)"

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_COLUMN

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True, warnings=[f"Dropping column {self.column_name} causes data loss."])

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP COLUMN {self.column_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object), is_destructive=True)]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ADD COLUMN {self.column_name} {self.previous_type};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class RenameColumn(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, old_name: str, new_name: str) -> None:
        super().__init__(target_object)
        self.old_name = old_name
        self.new_name = new_name

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.RENAME_COLUMN

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} RENAME COLUMN {self.old_name} TO {self.new_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} RENAME COLUMN {self.new_name} TO {self.old_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class ModifyColumn(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, column_name: str, new_type: str, old_type: str) -> None:
        super().__init__(target_object)
        self.column_name = column_name
        self.new_type = new_type
        self.old_type = old_type

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.MODIFY_COLUMN

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} TYPE {self.new_type};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} TYPE {self.old_type};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class AlterNullability(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, column_name: str, nullable: bool) -> None:
        super().__init__(target_object)
        self.column_name = column_name
        self.nullable = nullable

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ALTER_NULLABILITY

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        action = "DROP NOT NULL" if self.nullable else "SET NOT NULL"
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} {action};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        action = "SET NOT NULL" if self.nullable else "DROP NOT NULL"
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} {action};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class AlterDefault(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, column_name: str, new_default: Optional[str], old_default: Optional[str] = None) -> None:
        super().__init__(target_object)
        self.column_name = column_name
        self.new_default = new_default
        self.old_default = old_default

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ALTER_DEFAULT

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        clause = f"SET DEFAULT {self.new_default}" if self.new_default is not None else "DROP DEFAULT"
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} {clause};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        clause = f"SET DEFAULT {self.old_default}" if self.old_default is not None else "DROP DEFAULT"
        sql = f"ALTER TABLE {self.target_object} ALTER COLUMN {self.column_name} {clause};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


# --- Constraint Operations ---

class ChangePrimaryKey(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, new_pk_columns: List[str], old_pk_columns: Optional[List[str]] = None) -> None:
        super().__init__(target_object)
        self.new_pk_columns = new_pk_columns
        self.old_pk_columns = old_pk_columns or []

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CHANGE_PRIMARY_KEY

    def validate(self, schema_context: Any) -> ValidationResult:
        if not self.new_pk_columns:
            return ValidationResult(is_valid=False, errors=["Primary key must contain at least one column."])
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=f"PK_{self.target_object}", target=str(self.target_object), edge_type="HARD")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        stmts = []
        if self.old_pk_columns:
            stmts.append(DDLStatement(sql=f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.target_object.name}_pkey;", target_object=str(self.target_object)))
        stmts.append(DDLStatement(sql=f"ALTER TABLE {self.target_object} ADD PRIMARY KEY ({', '.join(self.new_pk_columns)});", target_object=str(self.target_object)))
        return stmts

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        stmts = [DDLStatement(sql=f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.target_object.name}_pkey;", target_object=str(self.target_object))]
        if self.old_pk_columns:
            stmts.append(DDLStatement(sql=f"ALTER TABLE {self.target_object} ADD PRIMARY KEY ({', '.join(self.old_pk_columns)});", target_object=str(self.target_object)))
        return stmts


class ChangeForeignKey(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, constraint_name: str, fk_columns: List[str], ref_table: str, ref_columns: List[str]) -> None:
        super().__init__(target_object)
        self.constraint_name = constraint_name
        self.fk_columns = fk_columns
        self.ref_table = ref_table
        self.ref_columns = ref_columns

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CHANGE_FOREIGN_KEY

    def validate(self, schema_context: Any) -> ValidationResult:
        if len(self.fk_columns) != len(self.ref_columns):
            return ValidationResult(is_valid=False, errors=["FK columns count must match referenced columns count."])
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=str(self.target_object), target=self.ref_table, edge_type="HARD")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ADD CONSTRAINT {self.constraint_name} FOREIGN KEY ({', '.join(self.fk_columns)}) REFERENCES {self.ref_table} ({', '.join(self.ref_columns)});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.constraint_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class AddUniqueConstraint(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, constraint_name: str, columns: List[str]) -> None:
        super().__init__(target_object)
        self.constraint_name = constraint_name
        self.columns = columns

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ADD_UNIQUE_CONSTRAINT

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ADD CONSTRAINT {self.constraint_name} UNIQUE ({', '.join(self.columns)});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.constraint_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropUniqueConstraint(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, constraint_name: str, columns: Optional[List[str]] = None) -> None:
        super().__init__(target_object)
        self.constraint_name = constraint_name
        self.columns = columns or []

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_UNIQUE_CONSTRAINT

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.constraint_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        if self.columns:
            sql = f"ALTER TABLE {self.target_object} ADD CONSTRAINT {self.constraint_name} UNIQUE ({', '.join(self.columns)});"
        else:
            sql = f"-- Rollback placeholder for {self.constraint_name}"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class AddCheckConstraint(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, constraint_name: str, check_expression: str) -> None:
        super().__init__(target_object)
        self.constraint_name = constraint_name
        self.check_expression = check_expression

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.ADD_CHECK_CONSTRAINT

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} ADD CONSTRAINT {self.constraint_name} CHECK ({self.check_expression});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.constraint_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropCheckConstraint(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, constraint_name: str, check_expression: Optional[str] = None) -> None:
        super().__init__(target_object)
        self.constraint_name = constraint_name
        self.check_expression = check_expression

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_CHECK_CONSTRAINT

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER TABLE {self.target_object} DROP CONSTRAINT {self.constraint_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        if self.check_expression:
            sql = f"ALTER TABLE {self.target_object} ADD CONSTRAINT {self.constraint_name} CHECK ({self.check_expression});"
        else:
            sql = f"-- Rollback placeholder for {self.constraint_name}"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


# --- Index Operations ---

class CreateIndex(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, index_name: str, columns: List[str], unique: bool = False) -> None:
        super().__init__(target_object)
        self.index_name = index_name
        self.columns = columns
        self.unique = unique

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CREATE_INDEX

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=self.index_name, target=str(self.target_object), edge_type="HARD")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        unq = "UNIQUE " if self.unique else ""
        sql = f"CREATE {unq}INDEX {self.index_name} ON {self.target_object} ({', '.join(self.columns)});"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"DROP INDEX {self.index_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropIndex(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, index_name: str, previous_columns: Optional[List[str]] = None) -> None:
        super().__init__(target_object)
        self.index_name = index_name
        self.previous_columns = previous_columns or []

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_INDEX

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"DROP INDEX {self.index_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        if self.previous_columns:
            sql = f"CREATE INDEX {self.index_name} ON {self.target_object} ({', '.join(self.previous_columns)});"
        else:
            sql = f"-- Rollback placeholder for index {self.index_name}"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class RenameIndex(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, old_name: str, new_name: str) -> None:
        super().__init__(target_object)
        self.old_name = old_name
        self.new_name = new_name

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.RENAME_INDEX

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER INDEX {self.old_name} RENAME TO {self.new_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"ALTER INDEX {self.new_name} RENAME TO {self.old_name};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


# --- Programmable Objects (Views, Sequences, Triggers) ---

class CreateView(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, view_query: str) -> None:
        super().__init__(target_object)
        self.view_query = view_query

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CREATE_VIEW

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"CREATE VIEW {self.target_object} AS {self.view_query};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"DROP VIEW {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropView(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, previous_query: Optional[str] = None) -> None:
        super().__init__(target_object)
        self.previous_query = previous_query

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_VIEW

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"DROP VIEW {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        if self.previous_query:
            sql = f"CREATE VIEW {self.target_object} AS {self.previous_query};"
        else:
            sql = f"-- Rollback placeholder for VIEW {self.target_object}"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class CreateSequence(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, start_with: int = 1, increment_by: int = 1) -> None:
        super().__init__(target_object)
        self.start_with = start_with
        self.increment_by = increment_by

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CREATE_SEQUENCE

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"CREATE SEQUENCE {self.target_object} START WITH {self.start_with} INCREMENT BY {self.increment_by};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"DROP SEQUENCE {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropSequence(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier) -> None:
        super().__init__(target_object)

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_SEQUENCE

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"DROP SEQUENCE {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"CREATE SEQUENCE {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class CreateTrigger(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, trigger_name: str, timing: str, event: str, body: str) -> None:
        super().__init__(target_object)
        self.trigger_name = trigger_name
        self.timing = timing
        self.event = event
        self.body = body

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.CREATE_TRIGGER

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return [DependencyEdge(source=self.trigger_name, target=str(self.target_object), edge_type="HARD")]

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"CREATE TRIGGER {self.trigger_name} {self.timing} {self.event} ON {self.target_object} FOR EACH ROW {self.body};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"DROP TRIGGER {self.trigger_name} ON {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]


class DropTrigger(BaseSchemaChange):
    def __init__(self, target_object: SchemaIdentifier, trigger_name: str) -> None:
        super().__init__(target_object)
        self.trigger_name = trigger_name

    @property
    def change_type(self) -> ChangeType:
        return ChangeType.DROP_TRIGGER

    def validate(self, schema_context: Any) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def analyze_dependencies(self) -> List[DependencyEdge]:
        return []

    def generate_forward_ddl(self) -> List[DDLStatement]:
        sql = f"DROP TRIGGER {self.trigger_name} ON {self.target_object};"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]

    def generate_rollback_ddl(self) -> List[DDLStatement]:
        sql = f"-- Rollback placeholder for trigger {self.trigger_name}"
        return [DDLStatement(sql=sql, target_object=str(self.target_object))]
