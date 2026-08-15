"""
Akaal — IBM Db2 Adapter (P4.2 Physical Reality)
================================================
Physical BaseAdapter implementation for IBM Db2 using ibm_db driver.
Strict Zero-Fake Policy: Requires physical IBM Db2 database connection.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.ibm_db2")


class IBMDB2Adapter(BaseAdapter):
    """
    Production-grade adapter for IBM Db2.
    Provides schema discovery, catalog inspection, batch operations, and transaction boundaries.
    """

    SYSTEM_TYPE = SystemType.IBM_DB2
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._conn = None
        self._in_transaction = False

    def _ensure_connected(self) -> None:
        if not self._conn or not self.is_connected:
            raise RuntimeError("IBM Db2 connection is not active.")

    async def connect(self) -> None:
        """Establishes physical connection to IBM Db2 server."""
        try:
            import ibm_db
        except ImportError as exc:
            self.is_connected = False
            raise RuntimeError("IBM Db2 physical driver 'ibm_db' is not installed.") from exc

        try:
            host = getattr(self.config, "host", "") or "localhost"
            port = getattr(self.config, "port", 50000) or 50000
            db_name = getattr(self.config, "database_name", "") or ""
            extra = getattr(self.config, "extra", {}) or {}
            username = extra.get("username", getattr(self.config, "username", ""))
            password = extra.get("password", getattr(self.config, "password", ""))

            conn_str = (
                f"DATABASE={db_name};"
                f"HOSTNAME={host};"
                f"PORT={port};"
                f"PROTOCOL=TCPIP;"
                f"UID={username};"
                f"PWD={password};"
            )
            self._conn = ibm_db.connect(conn_str, "", "")
            self.is_connected = True
            logger.info(f"[IBMDB2Adapter] Connected to physical IBM Db2 at {host}:{port}.")
        except Exception as exc:
            self.is_connected = False
            self._conn = None
            logger.error(f"[IBMDB2Adapter] Physical connection failed: {exc}")
            raise RuntimeError(f"Failed to connect to physical IBM Db2 database: {exc}") from exc

    async def close(self) -> None:
        if self._conn:
            try:
                import ibm_db
                ibm_db.close(self._conn)
            except Exception:
                pass
            self._conn = None
        self.is_connected = False
        self._in_transaction = False
        logger.info("[IBMDB2Adapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        try:
            import ibm_db
            stmt = ibm_db.exec_immediate(self._conn, "SELECT 1 FROM SYSIBM.SYSDUMMY1")
            return stmt is not None
        except Exception:
            return False

    async def get_server_version(self) -> str:
        self._ensure_connected()
        import ibm_db
        server_info = ibm_db.server_info(self._conn)
        return f"DB2 {getattr(server_info, 'DBMS_VER', 'v11.5')}"

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        import ibm_db
        extra = getattr(self.config, "extra", {}) or {}
        schema = extra.get("schema", getattr(self.config, "username", "DB2INST1")).upper()
        stmt = ibm_db.tables(self._conn, None, schema, "%", "TABLE")
        tables = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            tbl_name = row.get("TABLE_NAME")
            if tbl_name:
                tables.append(tbl_name)
            row = ibm_db.fetch_assoc(stmt)
        return tables

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        extra = getattr(self.config, "extra", {}) or {}
        schema = extra.get("schema", getattr(self.config, "username", "DB2INST1")).upper()
        tbl_upper = table_name.upper()
        stmt = ibm_db.columns(self._conn, None, schema, tbl_upper, "%")
        cols = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            cols.append({
                "name": row.get("COLUMN_NAME"),
                "type": str(row.get("TYPE_NAME")).upper(),
                "nullable": row.get("NULLABLE") == 1,
                "default": row.get("COLUMN_DEF"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return cols

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        sql = """
        SELECT CONSTNAME, TABNAME, FK_COLNAMES, PKTABNAME, PK_COLNAMES
        FROM SYSCAT.REFERENCES
        """
        stmt = ibm_db.exec_immediate(self._conn, sql)
        fks = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            fks.append({
                "constraint_name": row.get("CONSTNAME"),
                "table_name": row.get("TABNAME"),
                "column_name": row.get("FK_COLNAMES"),
                "foreign_table_name": row.get("PKTABNAME"),
                "foreign_column_name": row.get("PK_COLNAMES"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return fks

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f"SELECT INDNAME, UNIQUERULE, COLNAMES FROM SYSCAT.INDEXES WHERE TABNAME = '{tbl_upper}'"
        stmt = ibm_db.exec_immediate(self._conn, sql)
        indexes = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            indexes.append({
                "name": row.get("INDNAME"),
                "columns": str(row.get("COLNAMES")).strip().split("+")[1:],
                "unique": row.get("UNIQUERULE") in ("U", "P"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return indexes

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f"SELECT CONSTNAME, TYPE FROM SYSCAT.TABCONST WHERE TABNAME = '{tbl_upper}'"
        stmt = ibm_db.exec_immediate(self._conn, sql)
        constraints = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            constraints.append({
                "name": row.get("CONSTNAME"),
                "type": row.get("TYPE"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return constraints

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f"SELECT TRIGNAME, TEXT FROM SYSCAT.TRIGGERS WHERE TABNAME = '{tbl_upper}'"
        stmt = ibm_db.exec_immediate(self._conn, sql)
        triggers = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            triggers.append({
                "name": row.get("TRIGNAME"),
                "sql": row.get("TEXT"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return triggers

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        sql = "SELECT VIEWNAME, TEXT FROM SYSCAT.VIEWS"
        stmt = ibm_db.exec_immediate(self._conn, sql)
        views = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            views.append({
                "name": row.get("VIEWNAME"),
                "definition": row.get("TEXT"),
            })
            row = ibm_db.fetch_assoc(stmt)
        return views

    # ------------------------------------------------------------------
    # Data Operations & Bulk Extraction/Writing
    # ------------------------------------------------------------------

    async def _unique_key_columns(self, table_name: str) -> List[str]:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f"SELECT COLNAME FROM SYSCAT.INDEXES I JOIN SYSCAT.INDEXCOLUSE C ON I.INDSCHEMA = C.INDSCHEMA AND I.INDNAME = C.INDNAME WHERE I.TABNAME = '{tbl_upper}' AND (I.UNIQUERULE = 'P' OR I.UNIQUERULE = 'U') ORDER BY C.COLSEQ"
        stmt = ibm_db.exec_immediate(self._conn, sql)
        cols = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            cols.append(row.get("COLNAME"))
            row = ibm_db.fetch_assoc(stmt)
        return cols

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f'SELECT * FROM "{tbl_upper}" LIMIT {limit} OFFSET {offset}'
        stmt = ibm_db.exec_immediate(self._conn, sql)
        rows = []
        row = ibm_db.fetch_assoc(stmt)
        while row:
            rows.append(dict(row))
            row = ibm_db.fetch_assoc(stmt)
        return rows

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0

        import ibm_db
        tbl_upper = table_name.upper()
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join([f'"{c}"' for c in cols])
        sql = f'INSERT INTO "{tbl_upper}" ({col_names}) VALUES ({placeholders})'
        stmt = ibm_db.prepare(self._conn, sql)
        inserted_count = 0
        for r in rows:
            params = [r.get(c) for c in cols]
            res = ibm_db.execute(stmt, tuple(params))
            if res:
                inserted_count += 1
            else:
                err_msg = ibm_db.stmt_errormsg(stmt)
                raise RuntimeError(f"IBM Db2 physical write_batch failed for row: {err_msg}")
        return inserted_count

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f'SELECT COUNT(*) FROM "{tbl_upper}"'
        stmt = ibm_db.exec_immediate(self._conn, sql)
        row = ibm_db.fetch_tuple(stmt)
        return int(row[0]) if row else 0

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        import ibm_db
        tbl_upper = table_name.upper()
        sql = f'SELECT * FROM "{tbl_upper}"'
        stmt = ibm_db.exec_immediate(self._conn, sql)

        def _row_stream():
            row = ibm_db.fetch_assoc(stmt)
            while row:
                yield dict(row)
                row = ibm_db.fetch_assoc(stmt)

        return compute_canonical_table_checksum(_row_stream(), order_independent=True)

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        import ibm_db
        self._in_transaction = True
        ibm_db.autocommit(self._conn, ibm_db.SQL_AUTOCOMMIT_OFF)

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        if self._in_transaction:
            import ibm_db
            ibm_db.commit(self._conn)
            ibm_db.autocommit(self._conn, ibm_db.SQL_AUTOCOMMIT_ON)
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        if self._in_transaction:
            import ibm_db
            ibm_db.rollback(self._conn)
            ibm_db.autocommit(self._conn, ibm_db.SQL_AUTOCOMMIT_ON)
        self._in_transaction = False
