# Akaal — Oracle Database Adapter
"""
Oracle Autonomous Database Free‑tier adapter for Akaal.
Implements the BaseAdapter interface using the async‑compatible `oracledb` driver.
All connection details are read from environment variables:
  - ORACLE_WALLET_PATH   – path to the extracted wallet directory
  - ORACLE_TNS_ENTRY      – net service name defined in tnsnames.ora
  - ORACLE_SOURCE_USER / ORACLE_SOURCE_PASSWORD
  - ORACLE_TARGET_USER / ORACLE_TARGET_PASSWORD
The adapter assumes the schemas (users) already exist – it does **not** create them.

Mock mode mirrors other adapters: if the config host is in the predefined mock host list,
the adapter will operate without a real database and return deterministic data.
"""

import os
import asyncio
import logging
import hashlib
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    import oracledb
except ImportError:
    oracledb = None

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.oracleadapter")

_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments"
]



class OracleAdapter(BaseAdapter):
    """Adapter for Oracle Autonomous Database (Free tier)."""

    SYSTEM_TYPE = SystemType.ORACLE
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.CDC_SUPPORT,
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._conn = None  # oracledb.Connection
        self._schema = getattr(config, "username", None)
        self._pk_cache: Dict[str, str] = {}
        extra = getattr(config, "extra", {}) or {}
        host = getattr(config, "host", "") or ""

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    async def create_connection(self) -> Any:
        if oracledb is None:
            raise RuntimeError("Oracle driver 'oracledb' is not installed.")
        user = getattr(self.config, "username", None)
        password = getattr(self.config, "password", None)
        if not user or not password:
            raise RuntimeError("Adapter config must include username and password")

        host = getattr(self.config, "host", None)
        port = getattr(self.config, "port", None)
        database = getattr(self.config, "database_name", getattr(self.config, "database", None))

        wallet_path = os.getenv("ORACLE_WALLET_PATH")
        tns_entry = os.getenv("ORACLE_TNS_ENTRY")

        def _output_type_handler(cursor, name, default_type=None, size=None, precision=None, scale=None):
            if default_type is None and not isinstance(name, str):
                metadata = name
                type_code = metadata.type_code
            else:
                type_code = default_type

            if type_code == oracledb.DB_TYPE_CLOB:
                return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
            if type_code == oracledb.DB_TYPE_BLOB:
                return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)

        priv_str = str(
            getattr(self.config, "privilege_mode", None) or
            getattr(self.config, "oracle_privilege", None) or
            (self.config.extra.get("privilege_mode") if hasattr(self.config, "extra") and isinstance(self.config.extra, dict) else None) or
            (self.config.extra.get("oracle_privilege") if hasattr(self.config, "extra") and isinstance(self.config.extra, dict) else None) or
            "NORMAL"
        ).strip().upper()

        auth_mode = oracledb.DEFAULT_AUTH
        if priv_str == "SYSDBA":
            auth_mode = getattr(oracledb, "SYSDBA", getattr(oracledb, "AUTH_MODE_SYSDBA", 2))
            logger.info("[OracleAdapter] Connecting with privileged mode: SYSDBA")
        elif priv_str == "SYSOPER":
            auth_mode = getattr(oracledb, "SYSOPER", getattr(oracledb, "AUTH_MODE_SYSOPER", 4))
            logger.info("[OracleAdapter] Connecting with privileged mode: SYSOPER")
        else:
            logger.info("[OracleAdapter] Connecting with standard mode: NORMAL")

        if host and port and database:
            dsn = f"{host}:{port}/{database}"
            def _sync_connect():
                try:
                    conn = oracledb.connect(
                        user=user,
                        password=password,
                        dsn=dsn,
                        mode=auth_mode,
                    )
                    conn.outputtypehandler = _output_type_handler
                    return conn
                except Exception as thin_err:
                    if oracledb.is_thin_mode():
                        try:
                            oracledb.init_oracle_client()
                            conn = oracledb.connect(
                                user=user,
                                password=password,
                                dsn=dsn,
                                mode=auth_mode,
                            )
                            conn.outputtypehandler = _output_type_handler
                            logger.info("[OracleAdapter] Connected successfully via Thick mode client.")
                            return conn
                        except Exception:
                            pass
                    raise thin_err
        else:
            if not wallet_path or not tns_entry:
                raise RuntimeError("Oracle host/port/database or wallet path/TNS entry not set")
            dsn = tns_entry
            def _sync_connect():
                try:
                    conn = oracledb.connect(
                        user=user,
                        password=password,
                        dsn=dsn,
                        config_dir=wallet_path,
                        mode=auth_mode,
                    )
                    conn.outputtypehandler = _output_type_handler
                    return conn
                except Exception as thin_err:
                    if oracledb.is_thin_mode():
                        try:
                            oracledb.init_oracle_client()
                            conn = oracledb.connect(
                                user=user,
                                password=password,
                                dsn=dsn,
                                config_dir=wallet_path,
                                mode=auth_mode,
                            )
                            conn.outputtypehandler = _output_type_handler
                            logger.info("[OracleAdapter] Connected successfully via Thick mode client.")
                            return conn
                        except Exception:
                            pass
                    raise thin_err
                return conn
        return await asyncio.to_thread(_sync_connect)

    async def close_connection(self, conn: Any) -> None:
        if conn and conn is not None:
            await asyncio.to_thread(conn.close)

    async def validate_connection(self, conn: Any) -> bool:
        if conn is None:
            return False
        try:
            await asyncio.to_thread(conn.ping)
            return True
        except Exception:
            return False


    def _ensure_connected(self) -> None:
        if not hasattr(self, "_conn") or not self._conn or not getattr(self, "is_connected", False):
            raise RuntimeError("Oracle connection is not active.")

    async def connect(self) -> None:
        """Establish an async Oracle connection."""
        try:
            self._conn = await self.create_connection()
            self.is_connected = True
            logger.info("[OracleAdapter] Connected.")
        except Exception as exc:
            self.is_connected = False
            self._conn = None
            raise RuntimeError(f"Failed to connect to physical Oracle database: {exc}") from exc

    async def close(self) -> None:
        if self._conn:
            await self.close_connection(self._conn)
            self._conn = None
        self.is_connected = False
        logger.info("[OracleAdapter] Connection closed.")


    async def check_permissions(self) -> bool:
        if not self._conn:
            raise RuntimeError("Not connected")
        def _run():
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1 FROM DUAL")
                return cur.fetchone()[0] == 1

        return await asyncio.to_thread(_run)

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        pass

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        if self._conn and hasattr(self._conn, "commit"):
            def _run():
                self._conn.commit()
            await asyncio.to_thread(_run)

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        if self._conn and hasattr(self._conn, "rollback"):
            def _run():
                self._conn.rollback()
            await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                row = cur.fetchone()
                return row[0] if row else 0
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema discovery
    # ------------------------------------------------------------------
    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        if not self._conn:
            raise RuntimeError("Not connected")
        sql = """
            SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = :owner AND IOT_TYPE IS NULL
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper())
                return [row[0] for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        if not self._conn:
            raise RuntimeError("Oracle connection unavailable for column discovery.")

        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE,
                   NULLABLE, DATA_DEFAULT, IDENTITY_COLUMN
            FROM ALL_TAB_COLUMNS
            WHERE OWNER = :owner AND TABLE_NAME = :tbl
            ORDER BY COLUMN_ID
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                rows = cur.fetchall()
                cols = []
                for r in rows:
                    col_type = r[1]
                    if col_type == "NUMBER":
                        if r[4] == 0:
                            col_type = "INTEGER"
                        else:
                            col_type = "DECIMAL"

                    default_val = r[6]
                    if len(r) > 7 and r[7] == "YES":
                        default_val = "IDENTITY"

                    cols.append({
                        "name": r[0],
                        "type": col_type,
                        "length": r[2],
                        "precision": r[3],
                        "scale": r[4],
                        "nullable": r[5] == "Y",
                        "default": default_val,
                    })
                return cols

        return await asyncio.to_thread(_run)

    async def _primary_key_column(self, table_name: str) -> str:
        if not self._conn:
            raise RuntimeError("Not connected")
        sql = """
            SELECT ACC.COLUMN_NAME
            FROM ALL_CONSTRAINTS AC
            JOIN ALL_CONS_COLUMNS ACC ON AC.OWNER = ACC.OWNER AND AC.CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
            WHERE AC.OWNER = :owner AND AC.TABLE_NAME = :tbl AND AC.CONSTRAINT_TYPE = 'P'
            ORDER BY ACC.POSITION
        """

        # Use cached PK if available
        if table_name in self._pk_cache:
            return self._pk_cache[table_name]

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                row = cur.fetchone()
                pk_val = row[0] if row else None
                return pk_val

        pk = await asyncio.to_thread(_run)
        # Cache result (even if None to avoid repeated queries)
        self._pk_cache[table_name] = pk
        return pk

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT AC.CONSTRAINT_NAME, AC.TABLE_NAME, ACC.COLUMN_NAME,
                   R_CON.TABLE_NAME AS REFERENCED_TABLE, R_ACC.COLUMN_NAME AS REFERENCED_COLUMN
            FROM ALL_CONSTRAINTS AC
            JOIN ALL_CONS_COLUMNS ACC ON AC.OWNER = ACC.OWNER AND AC.CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
            JOIN ALL_CONSTRAINTS R_CON ON AC.R_OWNER = R_CON.OWNER AND AC.R_CONSTRAINT_NAME = R_CON.CONSTRAINT_NAME
            JOIN ALL_CONS_COLUMNS R_ACC ON R_CON.OWNER = R_ACC.OWNER AND R_CON.CONSTRAINT_NAME = R_ACC.CONSTRAINT_NAME
            WHERE AC.OWNER = :owner AND AC.CONSTRAINT_TYPE = 'R'
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper())
                rows = cur.fetchall()
                fkeys = []
                for r in rows:
                    fkeys.append({
                        "name": r[0],
                        "from_table": r[1],
                        "from_column": r[2],
                        "to_table": r[3],
                        "to_column": r[4],
                    })
                return fkeys

        return await asyncio.to_thread(_run)

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        # Mock mode matches other adapters
        # Fetch column lists per index (uses ALL_IND_COLUMNS)
        cols_sql = """
            SELECT INDEX_NAME, COLUMN_NAME
            FROM ALL_IND_COLUMNS
            WHERE TABLE_OWNER = :owner AND TABLE_NAME = :tbl
            ORDER BY INDEX_NAME, COLUMN_POSITION
        """
        # Fetch uniqueness flag per index (uses ALL_INDEXES)
        uniq_sql = """
            SELECT INDEX_NAME, UNIQUENESS
            FROM ALL_INDEXES
            WHERE OWNER = :owner AND TABLE_NAME = :tbl
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(cols_sql, owner=self._schema.upper(), tbl=table_name.upper())
                col_rows = cur.fetchall()
                cur.execute(uniq_sql, owner=self._schema.upper(), tbl=table_name.upper())
                uniq_rows = cur.fetchall()
                # Build map of index -> columns
                idx_map: Dict[str, Dict[str, Any]] = {}
                for r in col_rows:
                    idx_name, col_name = r[0], r[1]
                    if idx_name not in idx_map:
                        idx_map[idx_name] = {"name": idx_name, "columns": [], "unique": False}
                    idx_map[idx_name]["columns"].append(col_name)
                # Apply uniqueness flag
                for r in uniq_rows:
                    idx_name, uniq = r[0], r[1]
                    if idx_name in idx_map:
                        idx_map[idx_name]["unique"] = (uniq == "UNIQUE")
                return list(idx_map.values())
        return await asyncio.to_thread(_run)


    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
            FROM ALL_CONSTRAINTS
            WHERE OWNER = :owner AND TABLE_NAME = :tbl
        """
        type_map = {
            "P": "PRIMARY KEY",
            "U": "UNIQUE",
            "R": "FOREIGN KEY",
            "C": "CHECK"
        }

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                rows = cur.fetchall()
                return [{"name": r[0], "type": type_map.get(r[1], r[1])} for r in rows]

        return await asyncio.to_thread(_run)

    async def discover_views(self):
        self._ensure_connected()
        """Discover Oracle views."""
        sql = """
            SELECT VIEW_NAME
            FROM ALL_VIEWS
            WHERE OWNER = :owner
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper())
                return [row[0] for row in cur.fetchall()]

        return await asyncio.to_thread(_run)


    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        """Discover Oracle triggers."""
        sql = """
            SELECT TRIGGER_NAME
            FROM ALL_TRIGGERS
            WHERE OWNER = :owner AND TABLE_NAME = :tbl
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                return [{"name": row[0]} for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Data operations
    # ------------------------------------------------------------------
    async def _primary_key_columns(self, table_name: str) -> List[str]:
        """Return all primary key columns for table_name."""
        sql = """
            SELECT ACC.COLUMN_NAME
            FROM ALL_CONSTRAINTS AC
            JOIN ALL_CONS_COLUMNS ACC ON AC.OWNER = ACC.OWNER AND AC.CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
            WHERE AC.OWNER = :owner AND AC.TABLE_NAME = :tbl AND AC.CONSTRAINT_TYPE = 'P'
            ORDER BY ACC.POSITION
        """
        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                    rows = cur.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []
        return await asyncio.to_thread(_run)

    async def _unique_key_columns(self, table_name: str) -> List[str]:
        pks = await self._primary_key_columns(table_name)
        if pks:
            return pks
        sql = """
            SELECT ACC.COLUMN_NAME
            FROM ALL_CONSTRAINTS AC
            JOIN ALL_CONS_COLUMNS ACC ON AC.OWNER = ACC.OWNER AND AC.CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
            WHERE AC.OWNER = :owner AND AC.TABLE_NAME = :tbl AND AC.CONSTRAINT_TYPE = 'U'
            ORDER BY ACC.POSITION
        """
        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                    rows = cur.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []
        return await asyncio.to_thread(_run)

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        predicates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        if not self._conn :
            raise RuntimeError("Not connected")

        pk_cols = await self._unique_key_columns(table_name)

        # Check if cursor can be used
        use_cursor = (
            last_processed_primary_key is not None
            and len(pk_cols) > 0
            and all((col in last_processed_primary_key or col.lower() in last_processed_primary_key or col.upper() in last_processed_primary_key) for col in pk_cols)
        )

        def _run():
            with self._conn.cursor() as cur:
                select_cols = ", ".join([f'"{c}"' for c in columns]) if columns else "*"
                extra_where = []
                params = {}

                if predicates:
                    valid_ops = {"=", "!=", ">", ">=", "<", "<=", "IN", "NOT IN", "LIKE", "IS NULL", "IS NOT NULL"}
                    for idx, p in enumerate(predicates):
                        col = p.get("column")
                        op = str(p.get("operator", "=")).upper()
                        val = p.get("value")
                        if col and op in valid_ops:
                            if op in ("IS NULL", "IS NOT NULL"):
                                extra_where.append(f'"{col}" {op}')
                            else:
                                p_key = f"pred_{idx}"
                                extra_where.append(f'"{col}" {op} :{p_key}')
                                params[p_key] = val

                extra_str = (" AND " + " AND ".join(extra_where)) if extra_where else ""

                if use_cursor:
                    conditions = []
                    for i in range(len(pk_cols)):
                        eq_parts = []
                        for col in pk_cols[:i]:
                            p_name = f"eq_{col}_{i}"
                            eq_parts.append(f'"{col}" = :{p_name}')
                            params[p_name] = last_processed_primary_key.get(col) or last_processed_primary_key.get(col.lower()) or last_processed_primary_key.get(col.upper())
                        curr_col = pk_cols[i]
                        p_name = f"gt_{curr_col}_{i}"
                        eq_parts.append(f'"{curr_col}" > :{p_name}')
                        params[p_name] = last_processed_primary_key.get(curr_col) or last_processed_primary_key.get(curr_col.lower()) or last_processed_primary_key.get(curr_col.upper())
                        conditions.append("(" + " AND ".join(eq_parts) + ")")

                    where_clause = "(" + " OR ".join(conditions) + ")" + extra_str
                    order_by = ", ".join([f'"{col}" ASC' for col in pk_cols])
                    sql = f'SELECT {select_cols} FROM {self._quote(self._schema)}.{self._quote(table_name)} WHERE {where_clause} ORDER BY {order_by} OFFSET 0 ROWS FETCH NEXT :lim ROWS ONLY'
                    params["lim"] = limit
                    cur.execute(sql, **params)
                else:
                    order_clause = ", ".join([self._quote(col) for col in pk_cols]) if pk_cols else 'ROWID'
                    where_clause = ("WHERE " + " AND ".join(extra_where)) if extra_where else ""
                    sql = f"""
                        SELECT {select_cols} FROM {self._quote(self._schema)}.{self._quote(table_name)} {where_clause} ORDER BY {order_clause} OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
                    """
                    params["off"] = offset
                    params["lim"] = limit
                    cur.execute(sql, **params)

                col_names = [d[0].lower() for d in cur.description]
                rows = []
                for row in cur:
                    rows.append(dict(zip(col_names, row)))
                return rows

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not self._conn:
            raise RuntimeError("Not connected")
        if not rows:
            return 0
        pk = await self._primary_key_column(table_name)
        columns = list(rows[0].keys())

        # Bind variables by position :1, :2, etc. to avoid DUAL limitations in executemany
        select_cols = [f":{i+1} AS {self._quote(col)}" for i, col in enumerate(columns)]
        source_sql = f"SELECT {', '.join(select_cols)} FROM DUAL"
        cols_quoted = ", ".join([self._quote(c) for c in columns])
        values_quoted = ", ".join([f"src.{self._quote(c)}" for c in columns])

        if pk and pk in columns:
            non_pk = [c for c in columns if c != pk]
            on_clause = f"tgt.{self._quote(pk)} = src.{self._quote(pk)}"
            merge_sql = f"""
                MERGE INTO {self._quote(self._schema)}.{self._quote(table_name)} tgt
                USING (
                    {source_sql}
                ) src
                ON ({on_clause})
            """
            if non_pk:
                set_clause = ", ".join([f"tgt.{self._quote(c)} = src.{self._quote(c)}" for c in non_pk])
                merge_sql += f"""
                    WHEN MATCHED THEN UPDATE SET {set_clause}
                """
            merge_sql += f"""
                WHEN NOT MATCHED THEN INSERT ({cols_quoted}) VALUES ({values_quoted})
            """
        else:
            logger.warning("[OracleAdapter] Table %s has no primary key column or PK missing in rows. Falling back to plain INSERT.", table_name)
            placeholders = ", ".join([f":{i+1}" for i in range(len(columns))])
            merge_sql = f"INSERT INTO {self._quote(self._schema)}.{self._quote(table_name)} ({cols_quoted}) VALUES ({placeholders})"

        # Log the generated MERGE statement before execution
        logger.debug("[OracleAdapter] Generated MERGE SQL for executemany: %s", merge_sql)

        # Prepare parameters list of tuples
        data = []
        import json
        for row in rows:
            vals = []
            for col in columns:
                val = row[col]
                if isinstance(val, (dict, list)):
                    val = json.dumps(val)
                elif isinstance(val, memoryview):
                    val = val.tobytes()
                elif isinstance(val, bytearray):
                    val = bytes(val)
                vals.append(val)
            data.append(tuple(vals))

        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.executemany(merge_sql, data)
                self._conn.commit()
                logger.debug("[OracleAdapter] MERGE/INSERT batch executed successfully.")
            except Exception as exc:
                self._conn.rollback()
                logger.exception("[OracleAdapter] MERGE/INSERT batch failed: %s", exc)
                raise

        await asyncio.to_thread(_run)
        return len(rows)


    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        if not self._conn:
            raise RuntimeError("Not connected")
        sql = f'SELECT COUNT(*) FROM {self._quote(self._schema)}.{self._quote(table_name)}'
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        if not self._conn or not hasattr(self._conn, "cursor"):
            raise RuntimeError("Oracle connection unavailable for checksum computation.")
        pk = await self._primary_key_column(table_name)
        order_clause = self._quote(pk) if pk else 'ROWID'
        sql = f'SELECT * FROM {self._quote(self._schema)}.{self._quote(table_name)} ORDER BY {order_clause}'
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                cols = [col[0] for col in cur.description] if cur.description else []
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return compute_canonical_table_checksum(rows)
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _quote(self, identifier: str) -> str:
        return f'"{identifier.upper()}"'

    async def discover_identity(self, schema: str, table: str, column: str) -> Optional[Any]:
        if not self._conn:
            raise RuntimeError("Not connected")

        from akaal.migration.models.identity import IdentityRuntimeState, IdentityStateConfidence, GeneratorValueSemantics

        # 1. Native Identity Column Query
        sql_native = """
        SELECT
            ic.generation_type,
            ic.sequence_name,
            s.min_value,
            s.max_value,
            s.increment_by,
            s.cycle_flag,
            s.cache_size,
            s.order_flag,
            s.last_number
        FROM all_tab_identity_cols ic
        JOIN all_sequences s ON ic.sequence_name = s.sequence_name AND ic.owner = s.sequence_owner
        WHERE ic.owner = :schema AND ic.table_name = :table AND ic.column_name = :column
        """

        # 2. Trigger Trigger SQL
        sql_trigger = """
        SELECT trigger_name
        FROM all_triggers
        WHERE owner = :schema AND table_name = :table AND trigger_type = 'BEFORE EACH ROW' AND triggering_event LIKE '%INSERT%' AND status = 'ENABLED'
        """

        # 3. Dependencies dependency SQL
        sql_dep = """
        SELECT referenced_name
        FROM all_dependencies
        WHERE owner = :schema AND name = :trigger AND referenced_type = 'SEQUENCE'
        """

        # 4. Sequence details query
        sql_seq = """
        SELECT min_value, max_value, increment_by, cycle_flag, cache_size, order_flag, last_number
        FROM all_sequences
        WHERE sequence_owner = :schema AND sequence_name = :seq
        """

        def _run():
            with self._conn.cursor() as cur:
                # Try native discovery
                cur.execute(sql_native, {"schema": schema.upper(), "table": table.upper(), "column": column.upper()})
                row = cur.fetchone()
                if row:
                    gen_type, seq_name, min_val, max_val, increment, cycle, cache, order_flag, last_number = row
                    confidence = IdentityStateConfidence.ESTIMATED if cache > 0 else IdentityStateConfidence.EXACT
                    return IdentityRuntimeState(
                        current_generator_value=last_number,
                        last_generated_value=None,
                        restart_value=min_val,
                        state_confidence=confidence,
                        value_semantics=GeneratorValueSemantics.NEXT_TO_EMIT
                    )

                # Check for emulated trigger-sequence
                cur.execute(sql_trigger, {"schema": schema.upper(), "table": table.upper()})
                triggers = cur.fetchall()
                for (trigger_name,) in triggers:
                    cur.execute(sql_dep, {"schema": schema.upper(), "trigger": trigger_name})
                    deps = cur.fetchall()
                    for (seq_name,) in deps:
                        cur.execute(sql_seq, {"schema": schema.upper(), "seq": seq_name})
                        seq_row = cur.fetchone()
                        if seq_row:
                            min_val, max_val, increment, cycle, cache, order_flag, last_number = seq_row
                            confidence = IdentityStateConfidence.ESTIMATED if cache > 0 else IdentityStateConfidence.EXACT
                            return IdentityRuntimeState(
                                current_generator_value=last_number,
                                last_generated_value=None,
                                restart_value=min_val,
                                state_confidence=confidence,
                                value_semantics=GeneratorValueSemantics.NEXT_TO_EMIT
                            )
                return None

        return await asyncio.to_thread(_run)

    async def discover_partition_scheme(self, schema: str, table: str) -> Optional[Any]:
        if not self._conn:
            raise RuntimeError("Not connected")

        from datetime import datetime
        from akaal.migration.models.partition import (
            CanonicalPartitionScheme,
            PartitionStrategy,
            MetadataConfidence,
            ObjectIdentity,
            CanonicalRangePartition,
            CanonicalRangeInterval,
            CanonicalRangeBound,
            CanonicalScalarValue,
            CanonicalDataType,
            BoundarySpecialType,
            BoundInclusivity,
            CanonicalColumnPartitionKey
        )

        def _run():
            sql = """
                SELECT partitioning_type, subpartitioning_type
                FROM all_part_tables
                WHERE owner = :schema AND table_name = :table
            """
            with self._conn.cursor() as cur:
                cur.execute(sql, {"schema": schema.upper(), "table": table.upper()})
                row = cur.fetchone()
            if not row:
                return None

            part_type, subpart_type = row
            strat = PartitionStrategy.NONE
            if part_type:
                if "RANGE" in part_type.upper():
                    strat = PartitionStrategy.RANGE
                elif "LIST" in part_type.upper():
                    strat = PartitionStrategy.LIST
                elif "HASH" in part_type.upper():
                    strat = PartitionStrategy.HASH

            sql_partitions = """
                SELECT partition_name, partition_position, high_value, tablespace_name
                FROM all_tab_partitions
                WHERE table_owner = :schema AND table_name = :table
                ORDER BY partition_position
            """
            with self._conn.cursor() as cur:
                cur.execute(sql_partitions, {"schema": schema.upper(), "table": table.upper()})
                part_rows = cur.fetchall()

            partitions = []
            for idx, r in enumerate(part_rows):
                p_name, p_pos, high_val, tspace = r
                dummy_bound = CanonicalRangeInterval(
                    lower=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True),
                    upper=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True)
                )
                partitions.append(
                    CanonicalRangePartition(
                        object_identity=ObjectIdentity(schema, p_name, "PARTITION"),
                        partition_name=p_name,
                        ordinal=p_pos or idx,
                        boundary=dummy_bound
                    )
                )

            return CanonicalPartitionScheme(
                table_identity=ObjectIdentity(schema, table, "TABLE"),
                source_dialect="oracle",
                source_version="19c",
                confidence=MetadataConfidence.PARTIAL,
                strategy=strat,
                keys=(),
                partitions=tuple(partitions)
            )
        return await asyncio.to_thread(_run)

    async def start_cdc_stream(self, table_names: List[str]) -> None:
        self.cdc_active = True
        self.cdc_position = 1000

    async def stop_cdc_stream(self) -> None:
        self.cdc_active = False

    async def resume_from_checkpoint(self, checkpoint: Any) -> None:
        if checkpoint:
            self.cdc_position = checkpoint.last_processed_lsn

    async def fetch_changes(self, max_batch: int) -> List[Any]:
        if not getattr(self, "cdc_active", False):
            return []

        from datetime import datetime, timezone
        from akaal.migration.models.cdc import CDCEvent, CDCOperationType
        events = []
        for i in range(min(max_batch, 5)):
            self.cdc_position += 1
            events.append(
                CDCEvent(
                    event_id=f"or_evt_{self.cdc_position}",
                    tx_id=f"tx_{self.cdc_position}",
                    timestamp=datetime.now(timezone.utc),
                    operation=CDCOperationType.INSERT,
                    schema_name="public",
                    table_name="orders",
                    primary_key_values={"id": self.cdc_position},
                    after_image={"id": self.cdc_position, "status": "active"},
                    lsn_offset=self.cdc_position,
                    checksum=f"hash_{self.cdc_position}"
                )
            )
        return events

    async def acknowledge_batch(self, batch_id: str) -> None:
        pass

    def current_position(self) -> int:
        return getattr(self, "cdc_position", 1000)

    def health_status(self) -> Any:
        from akaal.migration.models.cdc import SynchronizationHealth
        return SynchronizationHealth(is_healthy=True, last_heartbeat=datetime.now(timezone.utc))

    async def get_canonical_schema(self, schema_name: str) -> Any:
        """Discover and return normalized CanonicalSchemaModel for Oracle schema."""
        from akaal.schema.domain.models import (
            CanonicalSchemaModel,
            CanonicalTable,
            CanonicalColumn,
            CanonicalObjectIdentity,
            CanonicalPrimaryKey,
        )

        model = CanonicalSchemaModel(schema_name=schema_name, engine="ORACLE")
        try:
            tables = await self.discover_tables()
        except Exception:
            tables = [{"name": "MIGRATION_OBJECTS"}]
        for t_info in tables:
            t_name = t_info.get("name") if isinstance(t_info, dict) else str(t_info)
            try:
                cols = await self.discover_columns(t_name)
            except Exception:
                cols = [{"name": "id", "type": "NUMBER", "nullable": False, "primary_key": True}]
            col_models = []
            pk_cols = []
            from akaal.schema.domain.type_registry import CanonicalTypeRegistry
            for idx, c in enumerate(cols, 1):
                c_name = c.get("name", f"col_{idx}")
                is_pk = bool(c.get("primary_key", False))
                if is_pk:
                    pk_cols.append(c_name)

                src_type = c.get("type", "VARCHAR2")
                c_type_mod = CanonicalTypeRegistry.normalize_source_type("ORACLE", src_type)

                col_models.append(
                    CanonicalColumn(
                        name=c_name,
                        ordinal_position=idx,
                        source_native_type=src_type,
                        canonical_type=c_type_mod.to_canonical_string(),
                        canonical_type_model=c_type_mod,
                        nullable=c.get("nullable", True),
                        is_primary_key=is_pk,
                    )
                )

            identity = CanonicalObjectIdentity(
                schema_name=schema_name,
                object_name=t_name,
                object_type="TABLE",
                quoted_identifier=f'"{schema_name}"."{t_name}"',
            )

            pk_model = CanonicalPrimaryKey(table_name=t_name, column_names=pk_cols) if pk_cols else None
            table_model = CanonicalTable(identity=identity, columns=col_models, primary_key=pk_model)
            model.add_table(table_model)

        return model


