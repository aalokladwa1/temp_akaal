"""
Database Aware Optimizer.
Consumes database-specific hints from adapters without implementing adapters directly.
"""

from typing import Dict, Any, Optional
from akaal.performance.optimizers.base import PluginOptimizer


class DatabaseAwareOptimizer(PluginOptimizer):
    """Adjusts transaction execution styles based on DBMS capabilities/hints."""

    def __init__(self) -> None:
        super().__init__("database")
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        # Load database driver hints from current configuration context
        db_hints = current_config.get("db_adapter_hints", {})
        db_type = db_hints.get("db_type", "").upper()

        new_ops = {}
        if db_type == "POSTGRESQL":
            # Postgres: enable fast COPY mode and disable WAL logs where applicable
            new_ops["db_write_method"] = "COPY"
            new_ops["postgresql_wal_tuning"] = True
        elif db_type == "ORACLE":
            # Oracle: configure direct path array DML writes
            new_ops["db_write_method"] = "ARRAY_DML"
            new_ops["oracle_direct_path"] = True
        elif db_type in ("MYSQL", "MARIADB"):
            # MySQL: enable bulk multi-row inserts
            new_ops["db_write_method"] = "BULK_INSERT"
            new_ops["mysql_binlog_bypass"] = True
        elif db_type == "MONGODB":
            # MongoDB: configure BulkWrite batches
            new_ops["db_write_method"] = "BULK_WRITE"

        if new_ops and any(current_config.get(k) != v for k, v in new_ops.items()):
            return new_ops
        return None
