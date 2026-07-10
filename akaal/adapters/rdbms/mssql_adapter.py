# Akaal — Microsoft SQL Server Adapter
# ====================================
# Fully implemented adapter for Microsoft SQL Server using aioodbc.
# Mirrors the behavior of PostgreSQLAdapter and MySQLAdapter.

import asyncio
import hashlib
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aioodbc

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.mssqladapter")

# Mock configuration – identical to other adapters for testing without a real DB
_MOCK_HOSTS = {
    "source-db.example.com",
    "source-prod.example.com",
    "target-db.example.com",
    "target-cloud.example.com",
    "connection-fail.example.com",
    "permission-fail.example.com",
    "large-db.example.com",
    "oracle-prod.example.com",
    "postgres-target.example.com",
}

_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments",
]

_MOCK_COLUMNS = {
    "users": [
        {"name": "id", "type": "INT", "nullable": False, "default": None, "parent_id": None},
        {"name": "email", "type": "NVARCHAR(255)", "nullable": False, "default": None, "parent_id": None},
        {"name": "password_hash", "type": "NVARCHAR(255)", "nullable": False, "default": None, "parent_id": None},
        {"name": "status", "type": "NVARCHAR(50)", "nullable": True, "default": "'active'", "parent_id": None},
        {"name": "created_at", "type": "DATETIME2", "nullable": True, "default": "GETDATE()", "parent_id": None},
    ],
    "orders": [
        {"name": "id", "type": "INT", "nullable": False, "default": None, "parent_id": None},
        {"name": "user_id", "type": "INT", "nullable": True, "default": None, "parent_id": "users.id"},
        {"name": "total_amount", "type": "DECIMAL(10,2)", "nullable": True, "default": None, "parent_id": None},
        {"name": "status", "type": "NVARCHAR(50)", "nullable": True, "default": "'pending'", "parent_id": None},
        {"name": "order_date", "type": "DATETIME2", "nullable": True, "default": "GETDATE()", "parent_id": None},
    ],
}


class MSSQLAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.MSSQL
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
        self.mock_mode = getattr(config, "host", "") in _MOCK_HOSTS
        if self.mock_mode:
            logger.info("[MSSQLAdapter] Mock mode: host=%s", config.host)
        self._pool: Optional[aioodbc.Pool] = None

    async def create_connection(self) -> Any:
        if self.mock_mode:
            if getattr(self.config, "host", "") == "connection-fail.example.com":
                raise ConnectionError("Mock: MSSQL connection failure.")
            return "mock_mssql_conn"
            
        user = getattr(self.config, "username", None) or os.environ.get("MSSQL_USERNAME", "sa")
        password = getattr(self.config, "password", None) or os.environ.get("MSSQL_PASSWORD", "")
        host = getattr(self.config, "host", "localhost")
        port = getattr(self.config, "port", 1433)
        database = getattr(self.config, "database_name", getattr(self.config, "database", "master"))

        import pyodbc
        drivers = pyodbc.drivers()
        driver = None
        for name in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
            if name in drivers:
                driver = name
                break
        if not driver:
            raise RuntimeError(
                f"No suitable Microsoft SQL Server ODBC Driver found. "
                f"Please install 'ODBC Driver 18 for SQL Server' or 'ODBC Driver 17 for SQL Server'. "
                f"Installed drivers: {drivers}"
            )

        trusted = getattr(self.config, "trusted_connection", "no")
        is_trusted = str(trusted).lower() in ("yes", "true")

        server_val = host
        if host not in (".", "localhost", "127.0.0.1") and port and port != 1433:
            server_val = f"{host},{port}"

        if is_trusted:
            dsn = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server_val};"
                f"DATABASE={database};"
                f"Trusted_Connection=Yes;"
                f"TrustServerCertificate=Yes;"
            )
        else:
            dsn = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server_val};"
                f"DATABASE={database};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=Yes;"
            )
        return await asyncio.to_thread(pyodbc.connect, dsn)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create an aioodbc connection pool.

        In mock mode we simply set is_connected=True and skip real network work.
        """
        if self.mock_mode:
            if getattr(self.config, "host", "") == "connection-fail.example.com":
                raise ConnectionError("Mock: MSSQL connection failure.")
            self.is_connected = True
            logger.info("[MSSQLAdapter] Connected (mock).")
            return

        user = getattr(self.config, "username", None) or os.environ.get("MSSQL_USERNAME", "sa")
        password = getattr(self.config, "password", None) or os.environ.get("MSSQL_PASSWORD", "")
        host = getattr(self.config, "host", "localhost")
        port = getattr(self.config, "port", 1433)
        database = getattr(self.config, "database_name", getattr(self.config, "database", "master"))

        import pyodbc
        drivers = pyodbc.drivers()
        driver = None
        for name in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
            if name in drivers:
                driver = name
                break
        if not driver:
            raise RuntimeError(
                f"No suitable Microsoft SQL Server ODBC Driver found. "
                f"Please install 'ODBC Driver 18 for SQL Server' or 'ODBC Driver 17 for SQL Server'. "
                f"Installed drivers: {drivers}"
            )

        trusted = getattr(self.config, "trusted_connection", "no")
        is_trusted = str(trusted).lower() in ("yes", "true")

        server_val = host
        if host not in (".", "localhost", "127.0.0.1") and port and port != 1433:
            server_val = f"{host},{port}"

        if is_trusted:
            dsn = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server_val};"
                f"DATABASE={database};"
                f"Trusted_Connection=Yes;"
                f"TrustServerCertificate=Yes;"
            )
        else:
            dsn = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server_val};"
                f"DATABASE={database};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=Yes;"
            )
        logger.debug("================================================================================")
        logger.debug("MSSQL DSN:")
        logger.debug("%s", dsn)
        logger.debug("================================================================================")
        self._pool = await aioodbc.create_pool(dsn=dsn, autocommit=False)
        self.is_connected = True
        logger.info("[MSSQLAdapter] Connected to real SQL Server at %s:%s/%s using driver %s.", host, port, database, driver)

    async def close(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
        self.is_connected = False
        logger.info("[MSSQLAdapter] Connection closed.")

    def _connection(self):
        class MSSQLConnectionContext:
            def __init__(self, adapter):
                self.adapter = adapter
                self.conn = None
                self.is_async = adapter._pool is not None

            async def __aenter__(self):
                if self.is_async:
                    self.conn = await self.adapter._pool.acquire()
                else:
                    self.conn = getattr(self.adapter, "_conn", None)
                    if self.conn is None:
                        raise RuntimeError("No active pool or connection available.")
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.is_async and self.conn is not None:
                    try:
                        await self.adapter._pool.release(self.conn)
                    except Exception:
                        pass

            async def execute(self, sql: str, params: Optional[tuple] = None) -> List[Any]:
                if self.is_async:
                    async with self.conn.cursor() as cur:
                        await cur.execute(sql, params or ())
                        return await cur.fetchall()
                else:
                    def _run():
                        with self.conn.cursor() as cur:
                            cur.execute(sql, params or ())
                            try:
                                return cur.fetchall()
                            except Exception:
                                return []
                    return await asyncio.to_thread(_run)
        return MSSQLConnectionContext(self)

    async def execute_raw(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> List[Any]:
        """Execute a raw SQL statement on a connection from the pool or active handle.
        Returns fetched rows if any, otherwise returns an empty list.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if not self._pool and getattr(self, "_conn", None) is None:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            return []
        async with self._connection() as conn_ctx:
            rows = await conn_ctx.execute(sql, params)
            if commit and not conn_ctx.is_async:
                def _commit():
                    conn_ctx.conn.commit()
                await asyncio.to_thread(_commit)
            return rows

    async def execute_raw_many(self, sql: str, rows: List[tuple], commit: bool = True) -> None:
        """Execute executemany for raw SQL on a connection from the pool or active handle."""
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if not self._pool and getattr(self, "_conn", None) is None:
            raise RuntimeError("Not connected.")
        async with self._connection() as conn_ctx:
            if conn_ctx.is_async:
                async with conn_ctx.conn.cursor() as cur:
                    await cur.executemany(sql, rows)
                    if commit:
                        await conn_ctx.conn.commit()
            else:
                def _run():
                    with conn_ctx.conn.cursor() as cur:
                        cur.executemany(sql, rows)
                        if commit:
                            conn_ctx.conn.commit()
                await asyncio.to_thread(_run)

    async def acquire_connection(self) -> Any:
        """Acquire a raw connection from the pool. Primarily for pool testing."""
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self._pool is not None:
            return await self._pool.acquire()
        conn = getattr(self, "_conn", None)
        if conn is None:
            raise RuntimeError("Not connected.")
        return conn

    async def release_connection(self, conn) -> None:
        """Release a raw connection back to the pool."""
        if self._pool:
            await self._pool.release(conn)

    async def check_permissions(self) -> bool:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            if getattr(self.config, "host", "") == "permission-fail.example.com":
                return False
            return True
        async with self._connection() as conn_ctx:
            await conn_ctx.execute("SELECT 1")
        return True

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    async def _run_query(self, sql: str, params: Optional[tuple] = None) -> List[Any]:
        async with self._connection() as conn_ctx:
            return await conn_ctx.execute(sql, params)

    async def _primary_key_column(self, table_name: str) -> str:
        """Return the first primary‑key column for *table_name*.
        Falls back to ``id`` if none is found.
        """
        sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = ?
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
            OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
        """
        rows = await self._run_query(sql, (table_name,))
        if rows:
            return rows[0][0]
        return "id"

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            host = getattr(self.config, "host", "")
            if host in ("large-db.example.com", "oracle-prod.example.com", "postgres-target.example.com"):
                return _LARGE_TABLES
            return ["users", "orders", "order_items"]
        sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_TYPE = 'BASE TABLE'
        """
        rows = await self._run_query(sql)
        return [r[0] for r in rows]

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            return _MOCK_COLUMNS.get(table_name, [{"name": "id", "type": "INT", "nullable": False, "default": None, "parent_id": None}])
        sql = """
            SELECT 
                c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH, 
                c.IS_NULLABLE, c.COLUMN_DEFAULT,
                sc.is_identity
            FROM INFORMATION_SCHEMA.COLUMNS c
            JOIN sys.objects so ON so.name = c.TABLE_NAME AND so.schema_id = SCHEMA_ID(c.TABLE_SCHEMA)
            JOIN sys.columns sc ON sc.object_id = so.object_id AND sc.name = c.COLUMN_NAME
            WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """
        rows = await self._run_query(sql, (table_name,))
        cols = []
        for r in rows:
            col_name, data_type, char_max_len, is_nullable, col_default, is_identity = r
            if char_max_len and data_type.upper() in ("VARCHAR", "NVARCHAR", "CHAR", "NCHAR"):
                type_str = f"{data_type.upper()}({char_max_len})"
            else:
                type_str = data_type.upper()
            if is_identity:
                col_default = "nextval"
            cols.append({
                "name": col_name,
                "type": type_str,
                "nullable": is_nullable == "YES",
                "default": col_default,
                "parent_id": None,
            })
        return cols

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [{"name": "fk_orders_user", "from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id"}]
        sql = """
            SELECT 
                fk.name AS constraint_name,
                tp.name AS table_name,
                cp.name AS column_name,
                tr.name AS referenced_table_name,
                cr.name AS referenced_column_name
            FROM 
                sys.foreign_keys fk
            INNER JOIN 
                sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN 
                sys.tables tp ON fkc.parent_object_id = tp.object_id
            INNER JOIN 
                sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN 
                sys.tables tr ON fkc.referenced_object_id = tr.object_id
            INNER JOIN 
                sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
        """
        rows = await self._run_query(sql)
        fkeys = []
        for r in rows:
            name, from_table, from_col, to_table, to_col = r
            fkeys.append({
                "name": name,
                "from_table": from_table,
                "from_column": from_col,
                "to_table": to_table,
                "to_column": to_col,
            })
        return fkeys

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [{"name": f"{table_name}_pkey", "columns": ["id"], "unique": True}]
        sql = """
            SELECT i.name AS index_name, c.name AS column_name, i.is_unique
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            WHERE t.name = ?
        """
        rows = await self._run_query(sql, (table_name,))
        indices_map: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            idx_name, col_name, is_unique = r
            if idx_name not in indices_map:
                indices_map[idx_name] = {"name": idx_name, "columns": [], "unique": bool(is_unique)}
            indices_map[idx_name]["columns"].append(col_name)
        return list(indices_map.values())

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        sql = """
            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?
        """
        rows = await self._run_query(sql, (table_name,))
        return [{"name": r[0], "type": r[1]} for r in rows]

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        sql = """
            SELECT name, OBJECT_DEFINITION(object_id) AS definition, type_desc
            FROM sys.triggers
            WHERE parent_id = OBJECT_ID(?)
        """
        rows = await self._run_query(sql, (table_name,))
        triggers = []
        for r in rows:
            name, definition, type_desc = r
            triggers.append({"name": name, "event": type_desc, "definition": definition})
        return triggers

    async def discover_views(self) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        sql = """
            SELECT TABLE_NAME, VIEW_DEFINITION
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = 'dbo'
        """
        rows = await self._run_query(sql)
        return [{"name": r[0], "definition": r[1]} for r in rows]

    # ------------------------------------------------------------------
    # Data Operations
    # ------------------------------------------------------------------

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        """Return all primary key columns for table_name."""
        if self.mock_mode:
            if table_name == "composite_table":
                return ["pk1", "pk2"]
            elif table_name == "uuid_table":
                return ["uuid_col"]
            elif table_name == "string_table":
                return ["str_col"]
            elif table_name == "no_pk_table":
                return []
            return ["id"]

        sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'dbo'
              AND TABLE_NAME = ?
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        try:
            rows = await self._run_query(sql, (table_name,))
            return [row[0] for row in rows] if rows else []
        except Exception:
            return ["id"]

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self.mock_mode:
            start_id = offset
            pk_cols = await self._primary_key_columns(table_name)
            if last_processed_primary_key and pk_cols:
                # Mock cursor progression logic
                if len(pk_cols) == 1:
                    pk_val = last_processed_primary_key.get(pk_cols[0])
                    if pk_val is not None:
                        if isinstance(pk_val, str) and "-" in pk_val:
                            try:
                                start_id = int(pk_val.split("-")[-1]) + 1
                            except ValueError:
                                start_id = offset
                        else:
                            try:
                                start_id = int(pk_val) + 1
                            except ValueError:
                                start_id = offset
                else:
                    # Composite key progress: mock using the first pk column
                    pk_val = last_processed_primary_key.get(pk_cols[0])
                    if pk_val is not None:
                        try:
                            start_id = int(pk_val) + 1
                        except ValueError:
                            start_id = offset
            
            # Enforce dynamic limit for mock table pagination
            mock_max_rows = getattr(self.config, "mock_max_rows", 250)
            if start_id >= mock_max_rows:
                return []
            if start_id + limit > 250:
                limit = mock_max_rows - start_id

            rows = []
            for i in range(start_id, start_id + limit):
                row = {"data": f"mock_row_{i}"}
                if table_name == "composite_table":
                    row["pk1"] = i
                    row["pk2"] = i * 10
                elif table_name == "uuid_table":
                    row["uuid_col"] = f"uuid-{i}"
                elif table_name == "string_table":
                    row["str_col"] = f"str-{i}"
                elif table_name == "no_pk_table":
                    row["data"] = f"mock_row_{i}"
                else:
                    row["id"] = i
                rows.append(row)
            return rows

        pk_cols = await self._primary_key_columns(table_name)
        
        # Check if cursor can be used
        use_cursor = (
            last_processed_primary_key is not None 
            and len(pk_cols) > 0 
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        if use_cursor:
            conditions = []
            params = []
            for i in range(len(pk_cols)):
                eq_parts = []
                for col in pk_cols[:i]:
                    eq_parts.append(f"[{col}] = ?")
                    params.append(last_processed_primary_key[col])
                curr_col = pk_cols[i]
                eq_parts.append(f"[{curr_col}] > ?")
                params.append(last_processed_primary_key[curr_col])
                conditions.append("(" + " AND ".join(eq_parts) + ")")
            
            where_clause = " OR ".join(conditions)
            order_by = ", ".join([f"[{col}] ASC" for col in pk_cols])
            sql = f"SELECT * FROM [{table_name}] WHERE {where_clause} ORDER BY {order_by} OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
            params.append(limit)
            bind_vals = tuple(params)
        else:
            order_by = ", ".join([f"[{col}] ASC" for col in pk_cols]) if pk_cols else "[id]"
            sql = f"SELECT * FROM [{table_name}] ORDER BY {order_by} OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
            bind_vals = (offset, limit)

        async with self._connection() as conn_ctx:
            if conn_ctx.is_async:
                async with conn_ctx.conn.cursor() as cur:
                    await cur.execute(sql, bind_vals)
                    col_names = [d[0] for d in cur.description]
                    result = []
                    async for row in cur:
                        result.append(dict(zip(col_names, row)))
            else:
                def _run():
                    with conn_ctx.conn.cursor() as cur:
                        cur.execute(sql, bind_vals)
                        col_names = [d[0] for d in cur.description]
                        result = []
                        for row in cur:
                            result.append(dict(zip(col_names, row)))
                        return result
                result = await asyncio.to_thread(_run)
        return result

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if self.mock_mode:
            logger.info("[MSSQLAdapter] Mock write: %d rows to %s", len(rows), table_name)
            return len(rows)
        if not rows:
            return 0

        table_name = table_name.lower()
        rows = [{k.lower(): v for k, v in r.items()} for r in rows]
        import json
        from decimal import Decimal
        def _json_default(obj):
            if isinstance(obj, Decimal):
                if obj % 1 == 0:
                    return int(obj)
                return float(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        serialized_rows = []
        for row in rows:
            new_row = {}
            for k, v in row.items():
                if isinstance(v, (dict, list)):
                    new_row[k] = json.dumps(v, default=_json_default)
                elif isinstance(v, memoryview):
                    new_row[k] = v.tobytes()
                elif isinstance(v, bytearray):
                    new_row[k] = bytes(v)
                else:
                    new_row[k] = v
            serialized_rows.append(new_row)
        rows = serialized_rows
        pk = await self._primary_key_column(table_name)
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        cols_sql = ", ".join([f"[{c}]" for c in columns])
        
        async with self._connection() as conn_ctx:
            if conn_ctx.is_async:
                async with conn_ctx.conn.cursor() as cur:
                    has_identity = False
                    try:
                        # Check identity property
                        await cur.execute("SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID(?)", (table_name,))
                        has_identity = (await cur.fetchone()) is not None
                        if has_identity:
                            await cur.execute(f"SET IDENTITY_INSERT [{table_name}] ON")
                            
                        # Branch based on PK presence
                        if pk and pk in columns:
                            non_pk = [c for c in columns if c != pk]
                            if non_pk:
                                merge_sql = f"""
                                    MERGE INTO [{table_name}] AS target
                                    USING (SELECT {placeholders}) AS source ({cols_sql})
                                    ON target.[{pk}] = source.[{pk}]
                                    WHEN MATCHED THEN UPDATE SET {', '.join([f'target.[{c}] = source.[{c}]' for c in non_pk])}
                                    WHEN NOT MATCHED THEN INSERT ({cols_sql}) VALUES ({placeholders});
                                """
                                for row in rows:
                                    vals = tuple(row[col] for col in columns)
                                    await cur.execute(merge_sql, vals * 2)
                            else:
                                merge_sql = f"""
                                    MERGE INTO [{table_name}] AS target
                                    USING (SELECT {placeholders}) AS source ({cols_sql})
                                    ON target.[{pk}] = source.[{pk}]
                                    WHEN NOT MATCHED THEN INSERT ({cols_sql}) VALUES ({placeholders});
                                """
                                for row in rows:
                                    vals = tuple(row[col] for col in columns)
                                    await cur.execute(merge_sql, vals * 2)
                        else:
                            logger.warning("[MSSQLAdapter] Table %s has no primary key column or PK missing in rows. Falling back to plain INSERT.", table_name)
                            insert_sql = f"INSERT INTO [{table_name}] ({cols_sql}) VALUES ({placeholders})"
                            data = [tuple(row[col] for col in columns) for row in rows]
                            await cur.executemany(insert_sql, data)
                            
                        await conn_ctx.conn.commit()
                    except Exception:
                        await conn_ctx.conn.rollback()
                        raise
                    finally:
                        if has_identity:
                            try:
                                await cur.execute(f"SET IDENTITY_INSERT [{table_name}] OFF")
                            except Exception:
                                pass
            else:
                def _run():
                    with conn_ctx.conn.cursor() as cur:
                        has_identity = False
                        try:
                            # Check identity property
                            cur.execute("SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID(?)", (table_name,))
                            has_identity = cur.fetchone() is not None
                            if has_identity:
                                cur.execute(f"SET IDENTITY_INSERT [{table_name}] ON")
                                
                            # Branch based on PK presence
                            if pk and pk in columns:
                                non_pk = [c for c in columns if c != pk]
                                if non_pk:
                                    merge_sql = f"""
                                        MERGE INTO [{table_name}] AS target
                                        USING (SELECT {placeholders}) AS source ({cols_sql})
                                        ON target.[{pk}] = source.[{pk}]
                                        WHEN MATCHED THEN UPDATE SET {', '.join([f'target.[{c}] = source.[{c}]' for c in non_pk])}
                                        WHEN NOT MATCHED THEN INSERT ({cols_sql}) VALUES ({placeholders});
                                    """
                                    for row in rows:
                                        vals = tuple(row[col] for col in columns)
                                        cur.execute(merge_sql, vals * 2)
                                else:
                                    merge_sql = f"""
                                        MERGE INTO [{table_name}] AS target
                                        USING (SELECT {placeholders}) AS source ({cols_sql})
                                        ON target.[{pk}] = source.[{pk}]
                                        WHEN NOT MATCHED THEN INSERT ({cols_sql}) VALUES ({placeholders});
                                    """
                                    for row in rows:
                                        vals = tuple(row[col] for col in columns)
                                        cur.execute(merge_sql, vals * 2)
                            else:
                                logger.warning("[MSSQLAdapter] Table %s has no primary key column or PK missing in rows. Falling back to plain INSERT.", table_name)
                                insert_sql = f"INSERT INTO [{table_name}] ({cols_sql}) VALUES ({placeholders})"
                                data = [tuple(row[col] for col in columns) for row in rows]
                                cur.executemany(insert_sql, data)
                                
                            conn_ctx.conn.commit()
                        except Exception:
                            conn_ctx.conn.rollback()
                            raise
                        finally:
                            if has_identity:
                                try:
                                    cur.execute(f"SET IDENTITY_INSERT [{table_name}] OFF")
                                except Exception:
                                    pass
                await asyncio.to_thread(_run)
        return len(rows)

    async def get_row_count(self, table_name: str) -> int:
        if self.mock_mode:
            counts = {"users": 200000, "orders": 300000, "order_items": 617070}
            return counts.get(table_name, 10000)
        sql = f"SELECT COUNT(*) FROM [{table_name}]"
        rows = await self._run_query(sql)
        return rows[0][0] if rows else 0

    async def compute_checksum(self, table_name: str) -> str:
        if self.mock_mode:
            return hashlib.sha256(table_name.encode()).hexdigest()
        def _row_hash(row: dict) -> str:
            parts = []
            for k in sorted(row.keys()):
                v = row[k]
                if isinstance(v, Decimal):
                    v = str(v)
                elif hasattr(v, "isoformat"):
                    v = v.isoformat()
                else:
                    v = str(v) if v is not None else ""
                parts.append(f"{k}={v}")
            return hashlib.sha256("|".join(parts).encode()).hexdigest()
        pk = await self._primary_key_column(table_name)
        sql = f"SELECT * FROM [{table_name}] ORDER BY [{pk}]"
        async with self._connection() as conn_ctx:
            if conn_ctx.is_async:
                async with conn_ctx.conn.cursor() as cur:
                    await cur.execute(sql)
                    col_names = [d[0] for d in cur.description]
                    combined_parts = []
                    async for row in cur:
                        row_dict = dict(zip(col_names, row))
                        combined_parts.append(_row_hash(row_dict))
            else:
                def _run():
                    with conn_ctx.conn.cursor() as cur:
                        cur.execute(sql)
                        col_names = [d[0] for d in cur.description]
                        combined_parts = []
                        for row in cur:
                            row_dict = dict(zip(col_names, row))
                            combined_parts.append(_row_hash(row_dict))
                        return combined_parts
                combined_parts = await asyncio.to_thread(_run)
        combined = "|".join(combined_parts)
        return hashlib.sha256(combined.encode()).hexdigest()
