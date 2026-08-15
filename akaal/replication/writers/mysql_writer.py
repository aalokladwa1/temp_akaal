"""
AKAAL Replication Engine — Canonical MySQL Physical Writer Module
==================================================================
High-performance MySQL fast-path batch writer using pymysql
parameterized executemany array binding with ON DUPLICATE KEY UPDATE.
"""

import logging
import time
from typing import Dict, Any, List, Tuple, Optional

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    pymysql = None
    HAS_PYMYSQL = False

from akaal.engine.spec import BatchMetadata
from akaal.replication.contracts import IPhysicalWriter, ConnectorCapability

logger = logging.getLogger("akaal.replication.writers.mysql_writer")


class MySQLPhysicalWriter(IPhysicalWriter):
    """
    Canonical High-performance MySQL physical writer using pymysql
    parameterized batch array binding with ON DUPLICATE KEY UPDATE.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self) -> None:
        user = self.params.get("username") or self.params.get("user") or "root"
        password = self.params.get("password") or ""
        host = self.params.get("host") or "127.0.0.1"
        if host in ("localhost", "::1"):
            host = "127.0.0.1"
        port = int(self.params.get("port") or 3306)
        dbname = self.params.get("database") or self.params.get("database_name") or "mysql"

        if self.params.get("mock_mode") or self.params.get("is_mock") or not HAS_PYMYSQL:
            from unittest.mock import MagicMock
            self.conn = MagicMock()
            self.cursor = self.conn.cursor.return_value
            return

        for attempt in range(5):
            try:
                self.conn = pymysql.connect(host=host, port=port, user=user, password=password, database=dbname)
                self.cursor = self.conn.cursor()
                return
            except Exception as e:
                if attempt == 4:
                    if self.params.get("allow_mock_fallback", False):
                        from unittest.mock import MagicMock
                        logger.warning(f"[MySQLPhysicalWriter] Test mock fallback triggered for {host}:{port}/{dbname}: {e}")
                        self.conn = MagicMock()
                        self.cursor = self.conn.cursor.return_value
                        return
                    raise e
                time.sleep(0.1 * (attempt + 1))

    def write_batch(
        self,
        table_name: str,
        columns: List[str],
        data: List[Tuple],
        batch_meta: BatchMetadata,
        pk_columns: Optional[List[str]] = None,
        target_schema: str = "mysql",
        page_size: int = 5000,
        allow_merge: bool = True,
    ) -> int:
        if not data:
            return 0

        clean_table = table_name.strip('`').lower()
        clean_schema = (target_schema or "mysql").strip('`').lower()
        quoted_cols = [f"`{c.strip('`').lower()}`" for c in columns]
        col_str = ", ".join(quoted_cols)
        placeholders = ", ".join(["%s"] * len(columns))

        upsert_clause = ""
        if allow_merge and pk_columns:
            non_pk_cols = [c.strip('`').lower() for c in columns if c.strip('`').lower() not in [pk.strip('`').lower() for pk in pk_columns]]
            if non_pk_cols:
                updates = [f"`{col}`=VALUES(`{col}`)" for col in non_pk_cols]
                upsert_clause = f" ON DUPLICATE KEY UPDATE {', '.join(updates)}"

        insert_sql = f"INSERT INTO `{clean_schema}`.`{clean_table}` ({col_str}) VALUES ({placeholders}){upsert_clause}"

        if hasattr(self.conn, "_mock_name") or type(self.conn).__name__ == "MagicMock":
            if not self.params.get("allow_test_mock_harness", False):
                raise RuntimeError("MySQLPhysicalWriter requires a valid physical database connection cursor. Mock fallback is disallowed in physical production writers.")
            logger.info(f"[MySQLPhysicalWriter MOCK] Wrote batch of {len(data)} rows to `{clean_schema}`.`{clean_table}`")
            return len(data)

        try:
            self.cursor.executemany(insert_sql, data)
            return len(data)
        except Exception as err:
            logger.warning(f"[MySQLPhysicalWriter] Vectorized executemany failed for {clean_schema}.{clean_table}: {err}. Falling back to single-row write...")
            written = 0
            for row in data:
                try:
                    self.cursor.execute(insert_sql, row)
                    written += 1
                except Exception:
                    pass
            return written

    def commit(self) -> None:
        if self.conn and hasattr(self.conn, "commit"):
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn and hasattr(self.conn, "rollback"):
            self.conn.rollback()

    def close(self) -> None:
        if self.cursor and hasattr(self.cursor, "close"):
            try:
                self.cursor.close()
            except Exception:
                pass
        if self.conn and hasattr(self.conn, "close"):
            try:
                self.conn.close()
            except Exception:
                pass

    def get_capabilities(self) -> ConnectorCapability:
        return ConnectorCapability(can_read=False, can_write=True, supports_upsert=True)
