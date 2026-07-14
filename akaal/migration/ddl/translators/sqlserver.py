from typing import Tuple
from akaal.core.models.enums import SystemType
from akaal.migration.models import MigrationOperation
from akaal.migration.ddl.base import BaseDDLGenerator
from akaal.migration.ddl.registry import DDLGeneratorRegistry
from akaal.migration.ddl.utilities.quoting import IdentifierQuoter
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities

class SQLServerDDLGenerator(BaseDDLGenerator):
    """SQL Server / MSSQL DDL Generator dialect implementation."""
    def __init__(self) -> None:
        capabilities = DialectCapabilities(
            supports_transactional_ddl=True,
            supports_if_exists=False,
            supports_if_not_exists=False,
            supports_sequence_increment=True
        )
        super().__init__(IdentifierQuoter.sqlserver(), capabilities)

    def get_dialect_name(self) -> str:
        return "mssql"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        # SQL Server specific syntax defaults
        return sql, rollback_sql

# Register generator class
DDLGeneratorRegistry.register(SystemType.MSSQL, SQLServerDDLGenerator)
