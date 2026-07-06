# -*- coding: utf-8 -*-
"""
fixtures.py
Reusable helper functions and validation helpers for live database smoke tests.
"""

import os
import subprocess
import time
import json
import logging
import pymysql
import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("akaal.tests.integration.fixtures")

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "rootpassword",
    "database": "akaal_smoke"
}

POSTGRES_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "postgres",
    "password": "postgrespassword",
    "database": "akaal_smoke"
}

# ----------------------------------------------------------------------
# Container & DB Startup Helpers
# ----------------------------------------------------------------------

def start_containers():
    """Start the Docker compose services for MySQL and PostgreSQL."""
    logger.info("Starting Docker containers...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    try:
        # Run docker compose up in background
        subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"Failed to start Docker containers via docker-compose: {err.stderr}") from err

    # Wait for MySQL and PostgreSQL to be healthy/responsive
    _wait_for_db("mysql", MYSQL_CONFIG)
    _wait_for_db("postgres", POSTGRES_CONFIG)
    logger.info("All containers are healthy and online.")

def stop_containers():
    """Shutdown and clean compose containers."""
    logger.info("Stopping Docker containers...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    try:
        subprocess.run(
            ["docker-compose", "down", "-v"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as err:
        logger.warning("Failed to stop compose containers: %s", err.stderr)

def _wait_for_db(db_type: str, config: dict, timeout: int = 45):
    """Wait for database port and connection checks to be valid."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            if db_type == "mysql":
                conn = pymysql.connect(
                    host=config["host"],
                    port=config["port"],
                    user=config["user"],
                    password=config["password"],
                    database=config["database"]
                )
                conn.ping(reconnect=True)
                conn.close()
                return
            elif db_type == "postgres":
                conn = psycopg2.connect(
                    host=config["host"],
                    port=config["port"],
                    user=config["user"],
                    password=config["password"],
                    dbname=config["database"]
                )
                conn.close()
                return
        except Exception:
            time.sleep(1.0)
    raise TimeoutError(f"Database {db_type} failed to become healthy within {timeout}s.")

# ----------------------------------------------------------------------
# Schema & Seed Loader Helpers
# ----------------------------------------------------------------------

def _get_dialect_sql(file_path: str, dialect: str) -> List[str]:
    """Parse DDL/DML sections matching [MYSQL_START]/[MYSQL_END] or [POSTGRES_START]/[POSTGRES_END]."""
    tag_start = f"-- [{dialect.upper()}_START]"
    tag_end = f"-- [{dialect.upper()}_END]"
    
    statements = []
    current_stmt = []
    capture = False
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(tag_start):
                capture = True
                continue
            elif stripped.startswith(tag_end):
                capture = False
                continue
            
            if capture:
                # Basic parsing to group multiple lines by semicolon
                if stripped.startswith("--") or not stripped:
                    continue
                current_stmt.append(line)
                if stripped.endswith(";"):
                    statements.append("".join(current_stmt).strip())
                    current_stmt = []
                    
    return statements

def reset_source_database(dialect: str, config: dict):
    """Clean the tables from database."""
    logger.info("Resetting %s source database...", dialect)
    tables = ["audit_logs", "order_items", "orders", "products", "users"]
    
    if dialect == "mysql":
        conn = pymysql.connect(**config)
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table};")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        conn.close()
    elif dialect == "postgres":
        conn = psycopg2.connect(
            host=config["host"], port=config["port"],
            user=config["user"], password=config["password"], dbname=config["database"]
        )
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        conn.commit()
        conn.close()

def reset_target_database(dialect: str, config: dict):
    reset_source_database(dialect, config)

def load_schema(dialect: str, config: dict, schema_file: str):
    """Load matching schema DDL statements."""
    statements = _get_dialect_sql(schema_file, dialect)
    if dialect == "mysql":
        conn = pymysql.connect(**config)
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        conn.close()
    elif dialect == "postgres":
        conn = psycopg2.connect(
            host=config["host"], port=config["port"],
            user=config["user"], password=config["password"], dbname=config["database"]
        )
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        conn.close()

def load_seed_data(dialect: str, config: dict, seed_file: str):
    """Load matching seed DML statements."""
    statements = _get_dialect_sql(seed_file, dialect)
    if dialect == "mysql":
        conn = pymysql.connect(**config)
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        conn.close()
    elif dialect == "postgres":
        conn = psycopg2.connect(
            host=config["host"], port=config["port"],
            user=config["user"], password=config["password"], dbname=config["database"]
        )
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        conn.close()

# ----------------------------------------------------------------------
# Assertion & Validation Helpers
# ----------------------------------------------------------------------

def validate_table_count(conn: Any, dialect: str, expected: int):
    """Assert number of tables in public/smoke schema is equal to expected."""
    if dialect == "mysql":
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES;")
            rows = cur.fetchall()
            tbl_count = len(rows)
    elif dialect == "postgres":
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            rows = cur.fetchall()
            tbl_count = len(rows)
            
    if tbl_count != expected:
        raise AssertionError(f"Expected {expected} tables, found {tbl_count} tables instead. Tables: {rows}")

def validate_row_count(conn: Any, dialect: str, table_name: str, expected: int):
    """Assert row count of table_name is equal to expected."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
        row = cur.fetchone()
        count = row[0] if isinstance(row, tuple) else row["COUNT(*)"] if isinstance(row, dict) else row
        
    if int(count) != expected:
        raise AssertionError(f"Table '{table_name}' expected {expected} rows, but database has {count} rows.")

def validate_constraints(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Verify primary key columns matching between source and target."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_pk(conn, dialect):
        with conn.cursor() as cur:
            if dialect == "mysql":
                cur.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY';")
                res = cur.fetchall()
                # res is list of dict or tuple
                if not res:
                    return []
                # In PyMySQL connection, dict cursor or tuple cursor is configurable
                return [r["Column_name"] if isinstance(r, dict) else r[4] for r in res]
            elif dialect == "postgres":
                cur.execute(f"""
                    SELECT a.attname
                    FROM   pg_index i
                    JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE  i.indrelid = '{table_name}'::regclass AND i.indisprimary;
                """)
                res = cur.fetchall()
                return [r[0] for r in res]
                
    src_pk = _get_pk(src_conn, src_dialect)
    tgt_pk = _get_pk(tgt_conn, tgt_dialect)
    
    if sorted(src_pk) != sorted(tgt_pk):
        raise AssertionError(
            f"Primary Key mismatch for table '{table_name}': "
            f"source PK={src_pk}, target PK={tgt_pk}"
        )

def validate_indexes(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Verify that index count is compatible (at least index count target >= source)."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_idx_count(conn, dialect):
        with conn.cursor() as cur:
            if dialect == "mysql":
                cur.execute(f"SHOW INDEX FROM {table_name};")
                res = cur.fetchall()
                names = {r["Key_name"] if isinstance(r, dict) else r[2] for r in res}
                return len(names)
            elif dialect == "postgres":
                cur.execute(f"SELECT indexname FROM pg_indexes WHERE tablename = '{table_name}';")
                res = cur.fetchall()
                return len(res)
                
    src_cnt = _get_idx_count(src_conn, src_dialect)
    tgt_cnt = _get_idx_count(tgt_conn, tgt_dialect)
    
    if tgt_cnt < src_cnt:
        raise AssertionError(
            f"Index count target mismatch for table '{table_name}': "
            f"source count={src_cnt}, target count={tgt_cnt}"
        )

def validate_json_columns(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str, col_name: str):
    """Assert structured JSON contents match between source and target for all rows."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_json_data(conn, dialect):
        with conn.cursor() as cur:
            cur.execute(f"SELECT id, {col_name} FROM {table_name} ORDER BY id;")
            res = cur.fetchall()
            data = {}
            for r in res:
                # normalize cursor output (tuple/dict formats)
                r_id = r[0] if isinstance(r, tuple) else r.get("id") or r.get("ID")
                val = r[1] if isinstance(r, tuple) else r.get(col_name) or r.get(col_name.upper())
                
                # PostgreSQL jsonb or MySQL json might yield raw strings or parsed dicts depending on driver
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except Exception:
                        pass
                data[r_id] = val
            return data

    src_json = _get_json_data(src_conn, src_dialect)
    tgt_json = _get_json_data(tgt_conn, tgt_dialect)
    
    for row_id, src_val in src_json.items():
        tgt_val = tgt_json.get(row_id)
        # Deep compare json structures
        if src_val != tgt_val:
            raise AssertionError(
                f"JSON payload mismatch in table '{table_name}' row {row_id}: "
                f"source={src_val}, target={tgt_val}"
            )

def validate_blob_columns(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str, col_name: str):
    """Assert binary BLOB contents match exactly."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_bytes_data(conn, dialect):
        with conn.cursor() as cur:
            cur.execute(f"SELECT id, {col_name} FROM {table_name} ORDER BY id;")
            res = cur.fetchall()
            data = {}
            for r in res:
                r_id = r[0] if isinstance(r, tuple) else r.get("id") or r.get("ID")
                val = r[1] if isinstance(r, tuple) else r.get(col_name) or r.get(col_name.upper())
                
                # PyMySQL returns bytes or bytearray; psycopg2 returns memoryview or bytes
                if isinstance(val, memoryview):
                    val = val.tobytes()
                elif isinstance(val, bytearray):
                    val = bytes(val)
                data[r_id] = val
            return data

    src_bytes = _get_bytes_data(src_conn, src_dialect)
    tgt_bytes = _get_bytes_data(tgt_conn, tgt_dialect)
    
    for row_id, src_val in src_bytes.items():
        tgt_val = tgt_bytes.get(row_id)
        if src_val != tgt_val:
            raise AssertionError(
                f"BLOB payload mismatch in table '{table_name}' row {row_id}: "
                f"source={src_val}, target={tgt_val}"
            )

def validate_foreign_keys(conn: Any, dialect: str, table_name: str):
    """Assert that foreign keys references are valid by checking matching record presence."""
    with conn.cursor() as cur:
        if table_name == "orders":
            cur.execute("SELECT user_id FROM orders WHERE user_id NOT IN (SELECT id FROM users);")
            res = cur.fetchall()
            if res:
                raise AssertionError(f"Foreign key violation on orders -> users: orphan user_ids: {res}")
        elif table_name == "order_items":
            cur.execute("SELECT order_id FROM order_items WHERE order_id NOT IN (SELECT id FROM orders);")
            res_orders = cur.fetchall()
            cur.execute("SELECT product_id FROM order_items WHERE product_id NOT IN (SELECT id FROM products);")
            res_products = cur.fetchall()
            if res_orders or res_products:
                raise AssertionError(
                    f"Foreign key violation on order_items: "
                    f"orphan order_ids={res_orders}, orphan product_ids={res_products}"
                )

def validate_data_integrity(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Compare general numeric, date, and text values for exact equality."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _fetch_all(conn, dialect):
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} ORDER BY id;")
            res = cur.fetchall()
            # If cursor returns tuples, we get list of lists; if dicts, list of dicts.
            # Normalize to list of tuples sorted by row key
            normalized = []
            for r in res:
                if isinstance(r, dict):
                    # Sort keys to produce deterministic tuple list
                    tuple_val = tuple(r[k] for k in sorted(r.keys()))
                else:
                    tuple_val = tuple(r)
                normalized.append(tuple_val)
            return normalized

    src_rows = _fetch_all(src_conn, src_dialect)
    tgt_rows = _fetch_all(tgt_conn, tgt_dialect)
    
    if len(src_rows) != len(tgt_rows):
        raise AssertionError(f"Total row mismatch: source={len(src_rows)}, target={len(tgt_rows)}")
        
    # Compare row-by-row count
    for i, (src_r, tgt_r) in enumerate(zip(src_rows, tgt_rows)):
        if len(src_r) != len(tgt_r):
            raise AssertionError(f"Row structure mismatch at index {i} on table {table_name}.")

def cleanup():
    """Ensure pools are cleared and containers stopped."""
    stop_containers()
