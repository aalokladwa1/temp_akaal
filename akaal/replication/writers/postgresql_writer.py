"""
AKAAL Replication Engine — Canonical PostgreSQL Physical Writer Module
=======================================================================
High-performance PostgreSQL fast-path vectorized array binding writer using
psycopg2.extras.execute_values with single-row isolation fallback on conflict.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
import psycopg2
import psycopg2.extras

from akaal.engine.spec import BatchMetadata
from akaal.replication.contracts import IPhysicalWriter, ConnectorCapability

logger = logging.getLogger("akaal.replication.writers.postgresql_writer")


class PostgreSQLPhysicalWriter(IPhysicalWriter):
    """
    Canonical High-performance PostgreSQL fast-path writer using psycopg2.extras.execute_values
    vectorized array binding with single-row isolation fallback on conflict.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self) -> None:
        user = self.params.get("username") or self.params.get("user") or "postgres"
        password = self.params.get("password")
        host = self.params.get("host") or "127.0.0.1"
        if host in ("localhost", "::1"):
            host = "127.0.0.1"
        port = int(self.params.get("port") or 5432)
        dbname = self.params.get("database") or self.params.get("database_name") or "postgres"

        if self.params.get("mock_mode") or self.params.get("is_mock"):
            from unittest.mock import MagicMock
            self.conn = MagicMock()
            self.cursor = self.conn.cursor.return_value
            return

        for attempt in range(5):
            try:
                self.conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
                self.cursor = self.conn.cursor()
                return
            except Exception as e:
                if attempt == 4:
                    if self.params.get("allow_mock_fallback", False) or self.params.get("mock_mode", False):
                        from unittest.mock import MagicMock
                        logger.warning(f"[PostgreSQLPhysicalWriter] Explicit test mock fallback triggered for {host}:{port}/{dbname}: {e}")
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
        target_schema: str = "public",
        page_size: int = 5000,
    ) -> int:
        if not data:
            return 0

        if hasattr(self.conn, "_mock_name") or type(self.conn).__name__ == "MagicMock":
            raise RuntimeError("PostgreSQLPhysicalWriter requires a valid physical database connection cursor. Mock fallback is disallowed in physical production writers.")

        cols_sql = ", ".join([f'"{c.lower()}"' for c in columns])
        target_table_ref = f'"{target_schema}"."{table_name.lower()}"'

        sql = f"INSERT INTO {target_table_ref} ({cols_sql}) VALUES %s"
        if allow_merge and pk_columns:
            pk_cols_sql = ", ".join([f'"{pk.lower()}"' for pk in pk_columns])
            non_pk_cols = [c for c in columns if c.lower() not in [pk.lower() for pk in pk_columns]]
            if non_pk_cols:
                update_set = ", ".join([f'"{c.lower()}" = EXCLUDED."{c.lower()}"' for c in non_pk_cols])
                sql += f" ON CONFLICT ({pk_cols_sql}) DO UPDATE SET {update_set}"
            else:
                sql += f" ON CONFLICT ({pk_cols_sql}) DO NOTHING"

        try:
            psycopg2.extras.execute_values(self.cursor, sql, data, page_size=page_size)
            logger.info(f"[POSTGRESQL PHYSICAL WRITER] Batch {batch_meta.batch_id}: Inserted {len(data)} rows into {target_table_ref}")
            return len(data)
        except Exception as err:
            logger.warning(f"[POSTGRESQL PHYSICAL WRITER] Vectorized batch insert failed for {batch_meta.batch_id}: {err}. Retrying row-by-row...")
            self.conn.rollback()

            inserted = 0
            single_sql = f"INSERT INTO {target_table_ref} ({cols_sql}) VALUES ({', '.join(['%s']*len(columns))})"
            if allow_merge and pk_columns:
                pk_cols_sql = ", ".join([f'"{pk.lower()}"' for pk in pk_columns])
                non_pk_cols = [c for c in columns if c.lower() not in [pk.lower() for pk in pk_columns]]
                if non_pk_cols:
                    update_set = ", ".join([f'"{c.lower()}" = EXCLUDED."{c.lower()}"' for c in non_pk_cols])
                    single_sql += f" ON CONFLICT ({pk_cols_sql}) DO UPDATE SET {update_set}"
                else:
                    single_sql += f" ON CONFLICT ({pk_cols_sql}) DO NOTHING"

            for row in data:
                try:
                    self.cursor.execute(single_sql, row)
                    inserted += 1
                except Exception as row_err:
                    logger.error(f"[POSTGRESQL PHYSICAL WRITER] Single row insert failed: {row_err}")
            return inserted

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn:
            self.conn.rollback()

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
