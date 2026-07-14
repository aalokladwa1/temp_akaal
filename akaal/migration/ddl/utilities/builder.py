from typing import List, Optional

class SQLBuilder:
    """
    Vendor-agnostic SQL structure generator. Assembles generic query fragments
    and templates without referencing dialect-specific syntax or properties.
    """

    def build_create_table(self, table_name: str, column_definitions: List[str]) -> str:
        """Assembles standard CREATE TABLE statement."""
        cols_joined = ", ".join(column_definitions)
        return f"CREATE TABLE {table_name} ({cols_joined})"

    def build_drop_table(self, table_name: str, if_exists: bool = False) -> str:
        """Assembles standard DROP TABLE statement."""
        exist_clause = " IF EXISTS" if if_exists else ""
        return f"DROP TABLE{exist_clause} {table_name}"

    def build_add_column(self, table_name: str, column_name: str, data_type: str) -> str:
        """Assembles standard ALTER TABLE ADD COLUMN statement."""
        return f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}"

    def build_drop_column(self, table_name: str, column_name: str) -> str:
        """Assembles standard ALTER TABLE DROP COLUMN statement."""
        return f"ALTER TABLE {table_name} DROP COLUMN {column_name}"

    def build_add_constraint(self, table_name: str, constraint_name: str, constraint_type: str) -> str:
        """Assembles standard ALTER TABLE ADD CONSTRAINT statement."""
        return f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} {constraint_type}"

    def build_drop_constraint(self, table_name: str, constraint_name: str) -> str:
        """Assembles standard ALTER TABLE DROP CONSTRAINT statement."""
        return f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"

    def build_create_index(self, index_name: str, table_name: str, columns: List[str], unique: bool = False) -> str:
        """Assembles standard CREATE INDEX statement."""
        uniq_clause = " UNIQUE" if unique else ""
        cols_joined = ", ".join(columns)
        return f"CREATE{uniq_clause} INDEX {index_name} ON {table_name} ({cols_joined})"

    def build_drop_index(self, index_name: str, table_name: Optional[str] = None) -> str:
        """Assembles standard DROP INDEX statement."""
        on_clause = f" ON {table_name}" if table_name else ""
        return f"DROP INDEX {index_name}{on_clause}"

    def build_create_view(self, view_name: str, definition: str) -> str:
        """Assembles standard CREATE VIEW statement."""
        return f"CREATE VIEW {view_name} AS {definition}"

    def build_drop_view(self, view_name: str) -> str:
        """Assembles standard DROP VIEW statement."""
        return f"DROP VIEW {view_name}"

    def build_create_sequence(self, seq_name: str, start: Optional[int] = None, increment: Optional[int] = None) -> str:
        """Assembles standard CREATE SEQUENCE statement."""
        clauses = [f"CREATE SEQUENCE {seq_name}"]
        if start is not None:
            clauses.append(f"START WITH {start}")
        if increment is not None:
            clauses.append(f"INCREMENT BY {increment}")
        return " ".join(clauses)

    def build_drop_sequence(self, seq_name: str) -> str:
        """Assembles standard DROP SEQUENCE statement."""
        return f"DROP SEQUENCE {seq_name}"

    def build_create_trigger(self, trigger_name: str, table_name: str, timing: str, event: str, definition: str) -> str:
        """Assembles standard CREATE TRIGGER statement."""
        return f"CREATE TRIGGER {trigger_name} {timing} {event} ON {table_name} {definition}"

    def build_drop_trigger(self, trigger_name: str, table_name: Optional[str] = None) -> str:
        """Assembles standard DROP TRIGGER statement."""
        on_clause = f" ON {table_name}" if table_name else ""
        return f"DROP TRIGGER {trigger_name}{on_clause}"
