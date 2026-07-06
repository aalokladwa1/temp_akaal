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

import oracledb

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.oracleadapter")

_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments"
]

_MOCK_COLUMNS = {
    "users": [
        {"name": "id",           "type": "INTEGER",      "nullable": False, "default": "nextval('users_id_seq')", "parent_id": None},
        {"name": "email",        "type": "VARCHAR(255)",  "nullable": False, "default": None,                     "parent_id": None},
        {"name": "password_hash","type": "VARCHAR(255)",  "nullable": False, "default": None,                     "parent_id": None},
        {"name": "status",       "type": "VARCHAR(50)",   "nullable": True,  "default": "'active'",               "parent_id": None},
        {"name": "created_at",   "type": "TIMESTAMP",     "nullable": True,  "default": "now()",                  "parent_id": None},
    ],
    "orders": [
        {"name": "id",           "type": "INTEGER",      "nullable": False, "default": "nextval('orders_id_seq')", "parent_id": None},
        {"name": "user_id",      "type": "INTEGER",      "nullable": True,  "default": None,                       "parent_id": "users.id"},
        {"name": "total_amount", "type": "NUMERIC(10,2)","nullable": True,  "default": None,                       "parent_id": None},
        {"name": "status",       "type": "VARCHAR(50)",  "nullable": True,  "default": "'pending'",                "parent_id": None},
        {"name": "order_date",   "type": "TIMESTAMP",    "nullable": True,  "default": "now()",                    "parent_id": None},
    ],
}

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
        # Consistent mock‑mode handling as other adapters
        self.mock_mode = getattr(config, "host", "") in _MOCK_HOSTS
        if self.mock_mode:
            logger.info("[OracleAdapter] Mock mode: host=%s", getattr(config, "host", ""))

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    async def create_connection(self) -> Any:
        if self.mock_mode:
            return "mock_oracle_conn"
        wallet_path = os.getenv("ORACLE_WALLET_PATH")
        tns_entry = os.getenv("ORACLE_TNS_ENTRY")
        if not wallet_path or not tns_entry:
            raise RuntimeError("Oracle wallet path or TNS entry not set in environment")
        user = getattr(self.config, "username", None)
        password = getattr(self.config, "password", None)
        if not user or not password:
            raise RuntimeError("Adapter config must include username and password")
        dsn = tns_entry
        def _sync_connect():
            return oracledb.connect(
                user=user,
                password=password,
                dsn=dsn,
                config_dir=wallet_path,
                mode=oracledb.DEFAULT_AUTH,
            )
        return await asyncio.to_thread(_sync_connect)

    async def close_connection(self, conn: Any) -> None:
        if conn and conn != "mock_oracle_conn":
            await asyncio.to_thread(conn.close)

    async def validate_connection(self, conn: Any) -> bool:
        if conn == "mock_oracle_conn":
            return True
        if conn is None:
            return False
        try:
            await asyncio.to_thread(conn.ping)
            return True
        except Exception:
            return False

    async def connect(self) -> None:
        """Establish an async Oracle connection using wallet credentials."""
        self._conn = await self.create_connection()
        self.is_connected = True
        logger.info("[OracleAdapter] Connected.")

    async def close(self) -> None:
        if self._conn:
            await self.close_connection(self._conn)
            self._conn = None
        self.is_connected = False
        logger.info("[OracleAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        if not self._conn:
            raise RuntimeError("Not connected")
        if self.mock_mode:
            # Mock permission failures mirror MySQL/PostgreSQL behavior
            if getattr(self.config, "host", "") == "permission-fail.example.com":
                return False
            return True

        def _run():
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1 FROM DUAL")
                return cur.fetchone()[0] == 1

        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema discovery
    # ------------------------------------------------------------------
    async def discover_tables(self) -> List[str]:
        if not self._conn:
            raise RuntimeError("Not connected")
        if self.mock_mode:
            host = getattr(self.config, "host", "")
            if host in ("large-db.example.com", "oracle-prod.example.com", "postgres-target.example.com"):
                return _LARGE_TABLES
            return ["users", "orders", "order_items"]

        sql = """
            SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = :owner AND IOT_TYPE IS NULL
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper())
                return [row[0] for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        if not self._conn:
            raise RuntimeError("Not connected")
        if self.mock_mode:
            return _MOCK_COLUMNS.get(table_name, [
                {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "parent_id": None}
            ])

        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE,
                   NULLABLE, DATA_DEFAULT
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
                    cols.append({
                        "name": r[0],
                        "type": r[1],
                        "length": r[2],
                        "precision": r[3],
                        "scale": r[4],
                        "nullable": r[5] == "Y",
                        "default": r[6],
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
        if self.mock_mode:
            return [
                {"name": "fk_orders_user", "from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id"}
            ]
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
        # Mock mode matches other adapters
        if self.mock_mode:
            return [{"name": f"{table_name}_pkey", "columns": ["id"], "unique": True}]
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
        if self.mock_mode:
            return []
        sql = """
            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
            FROM ALL_CONSTRAINTS
            WHERE OWNER = :owner AND TABLE_NAME = :tbl
        """

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, owner=self._schema.upper(), tbl=table_name.upper())
                rows = cur.fetchall()
                return [{"name": r[0], "type": r[1]} for r in rows]

        return await asyncio.to_thread(_run)
    
    async def discover_views(self):
        """Discover Oracle views."""
        if self.mock_mode:
            return []
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
        """Discover Oracle triggers."""
        if self.mock_mode:
            return []

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
        if self.mock_mode:
            if table_name == "composite_table":
                return ["PK1", "PK2"]
            elif table_name == "uuid_table":
                return ["UUID_COL"]
            elif table_name == "string_table":
                return ["STR_COL"]
            elif table_name == "no_pk_table":
                return []
            return ["ID"]

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
                return ["ID"]
        return await asyncio.to_thread(_run)

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self._conn and not self.mock_mode:
            raise RuntimeError("Not connected")
            
        if self.mock_mode:
            start_id = offset
            pk_cols = await self._primary_key_columns(table_name)
            if last_processed_primary_key and pk_cols:
                # Mock cursor progression logic
                first_pk = pk_cols[0]
                pk_val = last_processed_primary_key.get(first_pk) or last_processed_primary_key.get(first_pk.lower()) or last_processed_primary_key.get(first_pk.upper())
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
                    row["PK1"] = i
                    row["PK2"] = i * 10
                elif table_name == "uuid_table":
                    row["UUID_COL"] = f"uuid-{i}"
                elif table_name == "string_table":
                    row["STR_COL"] = f"str-{i}"
                elif table_name == "no_pk_table":
                    row["data"] = f"mock_row_{i}"
                else:
                    row["ID"] = i
                rows.append(row)
            return rows

        pk_cols = await self._primary_key_columns(table_name)
        
        # Check if cursor can be used
        use_cursor = (
            last_processed_primary_key is not None 
            and len(pk_cols) > 0 
            and all((col in last_processed_primary_key or col.lower() in last_processed_primary_key or col.upper() in last_processed_primary_key) for col in pk_cols)
        )

        def _run():
            with self._conn.cursor() as cur:
                if use_cursor:
                    conditions = []
                    params = {}
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
                    
                    where_clause = " OR ".join(conditions)
                    order_by = ", ".join([f'"{col}" ASC' for col in pk_cols])
                    sql = f'SELECT * FROM {self._quote(self._schema)}.{self._quote(table_name)} WHERE {where_clause} ORDER BY {order_by} OFFSET 0 ROWS FETCH NEXT :lim ROWS ONLY'
                    params["lim"] = limit
                    cur.execute(sql, **params)
                else:
                    order_clause = ", ".join([self._quote(col) for col in pk_cols]) if pk_cols else 'ROWID'
                    sql = f"""
                        SELECT * FROM {self._quote(self._schema)}.{self._quote(table_name)} ORDER BY {order_clause} OFFSET :off ROWS FETCH NEXT :lim ROWS ONLY
                    """
                    cur.execute(sql, off=offset, lim=limit)
                
                col_names = [d[0] for d in cur.description]
                rows = []
                for row in cur:
                    rows.append(dict(zip(col_names, row)))
                return rows

        return await asyncio.to_thread(_run)

        return await asyncio.to_thread(_run)

    def _build_merge_sql(self, table_name: str, columns: List[str], pk: str, non_pk: List[str], source_sql: str, cols_quoted: str) -> str:
        set_clause = ", ".join([f'tgt.{self._quote(c)} = src.{self._quote(c)}' for c in non_pk])
        merge_sql = f"""
            MERGE INTO {self._quote(self._schema)}.{self._quote(table_name)} tgt
            USING (
                {source_sql}
            ) src ({cols_quoted})
            ON (tgt.{self._quote(pk)} = src.{self._quote(pk)})
            WHEN MATCHED THEN UPDATE SET {set_clause}
            WHEN NOT MATCHED THEN INSERT ({cols_quoted}) VALUES ({', '.join([f'src.{self._quote(c)}' for c in columns])})
        """
        return merge_sql

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if not self._conn:
            raise RuntimeError("Not connected")
        if self.mock_mode:
            logger.info("[OracleAdapter] Mock write: %d rows to %s", len(rows), table_name)
            return len(rows)
        if not rows:
            return 0
        pk = await self._primary_key_column(table_name)
        columns = list(rows[0].keys())
        if not pk or pk not in columns:
            raise ValueError(f"MERGE requires primary key '{pk}' to be present in rows for table '{table_name}'.")
        bind_vals = []
        select_parts = []
        for row in rows:
            placeholders = []
            for col in columns:
                bind_vals.append(row[col])
                placeholders.append(f":{len(bind_vals)}")
            select_parts.append(f"SELECT {', '.join(placeholders)} FROM DUAL")
        source_sql = " UNION ALL ".join(select_parts)
        cols_quoted = ", ".join([self._quote(c) for c in columns])
        non_pk = [c for c in columns if c != pk]
        merge_sql = self._build_merge_sql(table_name, columns, pk, non_pk, source_sql, cols_quoted)
        # Log the generated MERGE statement before execution
        logger.debug("[OracleAdapter] Generated MERGE SQL: %s", merge_sql)

        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(merge_sql, bind_vals)
                self._conn.commit()
                logger.debug("[OracleAdapter] MERGE executed successfully.")
            except Exception as exc:
                self._conn.rollback()
                logger.exception("[OracleAdapter] MERGE failed: %s", exc)
                raise

        await asyncio.to_thread(_run)
        return len(rows)

    async def get_row_count(self, table_name: str) -> int:
        if not self._conn:
            raise RuntimeError("Not connected")
        sql = f'SELECT COUNT(*) FROM {self._quote(self._schema)}.{self._quote(table_name)}'
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        if not self._conn:
            raise RuntimeError("Not connected")
        pk = await self._primary_key_column(table_name)
        order_clause = self._quote(pk) if pk else 'ROWID'
        sql = f'SELECT * FROM {self._quote(self._schema)}.{self._quote(table_name)} ORDER BY {order_clause}'
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
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                col_names = [d[0] for d in cur.description]
                hashes = []
                for row in cur:
                    row_dict = dict(zip(col_names, row))
                    hashes.append(_row_hash(row_dict))
                return hashlib.sha256("|".join(hashes).encode()).hexdigest()
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _quote(self, identifier: str) -> str:
        return f'"{identifier.upper()}"'
