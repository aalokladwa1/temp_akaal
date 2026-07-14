from akaal.migration.ddl import (
    BaseDDLGenerator,
    PostgreSQLDDLGenerator,
    MySQLDDLGenerator,
    OracleDDLGenerator,
    SQLServerDDLGenerator,
    DDLGeneratorRegistry
)

def schema_prefix_index(dialect: str, schema_prefix: str, index_name: str, table_name: str) -> str:
    """Compatibility wrapper matching the original helper helper signature."""
    if dialect == "mysql":
        return f"{index_name} ON {schema_prefix}{table_name}"
    return f"{schema_prefix}{index_name}"

__all__ = [
    "BaseDDLGenerator",
    "PostgreSQLDDLGenerator",
    "MySQLDDLGenerator",
    "OracleDDLGenerator",
    "SQLServerDDLGenerator",
    "DDLGeneratorRegistry"
]
