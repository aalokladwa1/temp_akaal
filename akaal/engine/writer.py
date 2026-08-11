"""
AKAAL Engine Target Writer Module
==================================
Provides TargetWriter abstraction and high-performance PostgreSQL fast-path
vectorized array binding writer using psycopg2.extras.execute_values.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
import logging
import time
import psycopg2
import psycopg2.extras

from akaal.engine.spec import BatchMetadata

logger = logging.getLogger("akaal.engine.writer")


class TargetWriter(ABC):
    """Abstract interface for database target writing."""

    @abstractmethod
    def prepare_target_table(self, table_name: str, ddl_script: str, target_schema: str = "public") -> None:
        pass

    @abstractmethod
    def write_batch(
        self,
        table_name: str,
        columns: List[str],
        data: List[Tuple],
        batch_meta: BatchMetadata,
        pk_columns: Optional[List[str]] = None,
        target_schema: str = "public",
        page_size: int = 5000,
        allow_merge: bool = True,
    ) -> int:
        pass

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass

    @abstractmethod
    def verify_uncertain_batch(
        self,
        table_name: str,
        pk_column: str,
        first_pk: Any,
        last_pk: Any,
        expected_rows: int,
        target_schema: str = "public",
    ) -> str:
        """Verifies whether an un-acknowledged batch fully committed, failed, or is ambiguous."""
        pass

    @abstractmethod
    def reconcile_position(self, table_name: str, pk_column: str = "id", target_schema: str = "public") -> Any:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class PostgreSQLTargetWriter(TargetWriter):
    """
    High-performance PostgreSQL fast-path writer using psycopg2.extras.execute_values
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

        for attempt in range(5):
            try:
                self.conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
                self.cursor = self.conn.cursor()
                return
            except psycopg2.OperationalError as e:
                if attempt == 4:
                    raise e
                time.sleep(0.5 * (attempt + 1))

    def prepare_target_table(self, table_name: str, ddl_script: str, target_schema: str = "public") -> None:
        if not self.conn:
            self._connect()

        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}";')
                cur.execute(ddl_script)

    def write_batch(
        self,
        table_name: str,
        columns: List[str],
        data: List[Tuple],
        batch_meta: BatchMetadata,
        pk_columns: Optional[List[str]] = None,
        target_schema: str = "public",
        page_size: int = 5000,
        allow_merge: bool = True,
    ) -> int:
        if not data:
            return 0

        if not self.conn:
            self._connect()

        tbl_lower = table_name.lower()
        target_schema = target_schema.lower()

        # Dynamic Schema & Table Structure Preparation
        with self.conn.cursor() as prep_cur:
            prep_cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}";')
            cols_ddl = ", ".join([f'"{c.lower()}" TEXT' for c in columns])
            prep_cur.execute(f'CREATE TABLE IF NOT EXISTS "{target_schema}"."{tbl_lower}" ({cols_ddl});')
            for c in columns:
                try:
                    prep_cur.execute(f'ALTER TABLE "{target_schema}"."{tbl_lower}" ADD COLUMN IF NOT EXISTS "{c.lower()}" TEXT;')
                except Exception:
                    pass
        self.conn.commit()

        col_str = ", ".join([f'"{c.lower()}"' for c in columns])
        
        on_conflict_clause = ""
        if allow_merge and pk_columns:
            pk_str = ", ".join([f'"{p.lower()}"' for p in pk_columns])
            on_conflict_clause = f' ON CONFLICT ({pk_str}) DO NOTHING'

        sql = f'INSERT INTO "{target_schema}"."{tbl_lower}" ({col_str}) VALUES %s{on_conflict_clause}'

        try:
            psycopg2.extras.execute_values(self.cursor, sql, data, page_size=page_size)
            return len(data)
        except Exception as ex:
            logger.warning(f"[POSTGRES WRITER] Vectorized execute_values failed on {table_name}: {ex}. Triggering single-row isolation retry...")
            self.conn.rollback()

            # Single-row isolation fallback
            placeholders = ", ".join(["%s" for _ in columns])
            single_sql = f'INSERT INTO "{target_schema}"."{table_name}" ({col_str}) VALUES ({placeholders}){on_conflict_clause}'

            written_count = 0
            for single_row in data:
                try:
                    self.cursor.execute(single_sql, single_row)
                    self.conn.commit()
                    written_count += 1
                except Exception as s_ex:
                    self.conn.rollback()
                    logger.error(f"[POSTGRES WRITER] Isolated bad row skipped in {table_name}: {s_ex}")

            return written_count

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn:
            self.conn.rollback()

    def verify_uncertain_batch(
        self,
        table_name: str,
        pk_column: str,
        first_pk: Any,
        last_pk: Any,
        expected_rows: int,
        target_schema: str = "public",
    ) -> str:
        if not self.conn:
            self._connect()

        if first_pk is None or last_pk is None:
            return "AMBIGUOUS"

        with self.conn.cursor() as cur:
            cur.execute(
                f'SELECT COUNT(*) FROM "{target_schema}"."{table_name}" WHERE "{pk_column.lower()}" >= %s AND "{pk_column.lower()}" <= %s',
                (first_pk, last_pk)
            )
            row = cur.fetchone()
            count = row[0] if row else 0

        if count == expected_rows:
            return "COMMITTED"
        elif count == 0:
            return "NOT_COMMITTED"
        else:
            return "AMBIGUOUS"

    def reconcile_position(self, table_name: str, pk_column: str = "id", target_schema: str = "public") -> Any:
        if not self.conn:
            self._connect()

        with self.conn.cursor() as cur:
            cur.execute(f'SELECT COALESCE(MAX("{pk_column.lower()}"), 0) FROM "{target_schema}"."{table_name}"')
            row = cur.fetchone()
            return row[0] if row else 0

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
