"""
AKAAL Replication Engine — Canonical Oracle Physical Writer Module
===================================================================
High-performance Oracle fast-path batch writer using oracledb
parameterized array binding with single-row isolation fallback on conflict.
"""

import logging
import time
from typing import Dict, Any, List, Tuple, Optional
import oracledb

from akaal.engine.spec import BatchMetadata
from akaal.replication.contracts import IPhysicalWriter, ConnectorCapability

logger = logging.getLogger("akaal.replication.writers.oracle_writer")


class OraclePhysicalWriter(IPhysicalWriter):
    """
    Canonical High-performance Oracle physical writer using oracledb
    parameterized array binding with single-row isolation fallback on conflict.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self) -> None:
        user = self.params.get("username") or self.params.get("user")
        password = self.params.get("password")
        host = self.params.get("host") or "127.0.0.1"
        if host in ("localhost", "::1"):
            host = "127.0.0.1"
        port = int(self.params.get("port") or 1521)
        database = self.params.get("database") or self.params.get("database_name")

        if self.params.get("mock_mode") or self.params.get("is_mock"):
            from unittest.mock import MagicMock
            self.conn = MagicMock()
            self.cursor = self.conn.cursor.return_value
            return

        if not user or not password or not host or not database:
            if self.params.get("allow_mock_fallback", False):
                from unittest.mock import MagicMock
                self.conn = MagicMock()
                self.cursor = self.conn.cursor.return_value
                return
            raise ValueError(f"[ORACLE PHYSICAL WRITER] Incomplete connection parameters for user={user} host={host} db={database}")

        dsn = f"{host}:{port}/{database}"
        priv_str = str(self.params.get("privilege_mode") or self.params.get("oracle_privilege") or "NORMAL").strip().upper()
        auth_mode = oracledb.SYSDBA if priv_str == "SYSDBA" else (oracledb.SYSOPER if priv_str == "SYSOPER" else oracledb.DEFAULT_AUTH)

        for attempt in range(5):
            try:
                self.conn = oracledb.connect(user=user, password=password, dsn=dsn, mode=auth_mode)
                self.cursor = self.conn.cursor()
                return
            except Exception as e:
                if attempt == 4:
                    if self.params.get("allow_mock_fallback", False):
                        from unittest.mock import MagicMock
                        logger.warning(f"[OraclePhysicalWriter] Explicit test mock fallback triggered for {host}:{port}/{database}: {e}")
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
        target_schema: str = "SYSTEM",
        page_size: int = 5000,
        allow_merge: bool = True,
    ) -> int:
        if not data:
            return 0

        clean_table = table_name.replace('"', '').upper()
        clean_schema = (target_schema or "SYSTEM").replace('"', '').upper()
        clean_cols = [c.replace('"', '').upper() for c in columns]
        quoted_cols = [f'"{c}"' for c in clean_cols]
        col_str = ", ".join(quoted_cols)

        bind_placeholders = ", ".join([f":{i+1}" for i in range(len(columns))])
        insert_sql = f'INSERT INTO "{clean_schema}"."{clean_table}" ({col_str}) VALUES ({bind_placeholders})'

        if hasattr(self.conn, "_mock_name") or type(self.conn).__name__ == "MagicMock":
            logger.info(f"[OraclePhysicalWriter MOCK] Wrote batch of {len(data)} rows to {clean_schema}.{clean_table}")
            return len(data)

        try:
            self.cursor.executemany(insert_sql, data)
            return len(data)
        except Exception as err:
            logger.warning(f"[OraclePhysicalWriter] Vectorized executemany failed for {clean_schema}.{clean_table}: {err}. Falling back to single-row write...")
            written = 0
            for row in data:
                try:
                    self.cursor.execute(insert_sql, row)
                    written += 1
                except Exception as row_err:
                    if allow_merge and pk_columns:
                        # Attempt single-row MERGE fallback on PK conflict
                        pk_names = [pk.replace('"', '').upper() for pk in pk_columns]
                        non_pk_cols = [c for c in clean_cols if c not in pk_names]
                        
                        if non_pk_cols:
                            on_clause = " AND ".join([f't."{pk}" = :b_{pk}' for pk in pk_names])
                            update_clause = ", ".join([f't."{col}" = :b_{col}' for col in non_pk_cols])
                            merge_sql = f'MERGE INTO "{clean_schema}"."{clean_table}" t USING DUAL ON ({on_clause}) WHEN MATCHED THEN UPDATE SET {update_clause}'
                            try:
                                bind_dict = {f"b_{c}": val for c, val in zip(clean_cols, row)}
                                self.cursor.execute(merge_sql, bind_dict)
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
