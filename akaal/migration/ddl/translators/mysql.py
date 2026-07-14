from typing import Tuple
from akaal.core.models.enums import SystemType
from akaal.migration.models import MigrationOperation
from akaal.migration.ddl.base import BaseDDLGenerator
from akaal.migration.ddl.registry import DDLGeneratorRegistry
from akaal.migration.ddl.utilities.quoting import IdentifierQuoter
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities

class MySQLDDLGenerator(BaseDDLGenerator):
    """MySQL/MariaDB DDL Generator dialect implementation."""
    def __init__(self) -> None:
        capabilities = DialectCapabilities(
            supports_transactional_ddl=False,
            supports_if_exists=True,
            supports_if_not_exists=True,
            requires_index_table_on_drop=True
        )
        super().__init__(IdentifierQuoter.mysql(), capabilities)

    def get_dialect_name(self) -> str:
        return "mysql"

    def _format_dialect_sql(self, sql: str, rollback_sql: str, op: MigrationOperation) -> Tuple[str, str]:
        # MySQL specific syntax updates
        if "ADD COLUMN" in sql:
            sql = sql.replace("ADD COLUMN", "ADD")
        if "ALTER COLUMN" in sql:
            sql = sql.replace("ALTER COLUMN", "MODIFY")
            
        if rollback_sql:
            if "ADD COLUMN" in rollback_sql:
                rollback_sql = rollback_sql.replace("ADD COLUMN", "ADD")
            if "ALTER COLUMN" in rollback_sql:
                rollback_sql = rollback_sql.replace("ALTER COLUMN", "MODIFY")
                
        return sql, rollback_sql

# Register generator class
DDLGeneratorRegistry.register(SystemType.MYSQL, MySQLDDLGenerator)
DDLGeneratorRegistry.register(SystemType.MARIADB, MySQLDDLGenerator)
