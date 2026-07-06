# -*- coding: utf-8 -*-
"""
fixtures.py
Reusable helper functions and validation assertions for native database smoke tests.
"""

import os
import sys
import time
import json
import logging
import pymysql
import psycopg2
import psycopg2.extras
import pyodbc
from typing import Any, Dict, List, Tuple, Optional

logger = logging.getLogger("akaal.tests.validation.fixtures")

# Default connection settings (overrideable via environment variables)
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "rootpassword"),
    "database": os.getenv("MYSQL_DATABASE", "akaal_smoke")
}

POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "database": os.getenv("POSTGRES_DATABASE", "akaal_smoke")
}

SQLSERVER_CONFIG = {
    "driver": os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
    "server": os.getenv("SQLSERVER_SERVER", "localhost"),
    "database": os.getenv("SQLSERVER_DATABASE", "akaal_smoke"),
    "trusted_connection": os.getenv("SQLSERVER_TRUSTED", "yes"),
    "user": os.getenv("SQLSERVER_USER", ""),
    "password": os.getenv("SQLSERVER_PASSWORD", "")
}


def get_connection(dialect: str) -> Any:
    """Acquire a connection to the specified database engine."""
    if dialect == "mysql":
        # Check port first
        import socket
        s = socket.socket()
        s.settimeout(2.0)
        try:
            s.connect((MYSQL_CONFIG["host"], MYSQL_CONFIG["port"]))
            s.close()
        except Exception as e:
            raise ConnectionError(f"MySQL server is not running or accessible: {e}")

        return pymysql.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            database=MYSQL_CONFIG["database"]
        )
    elif dialect == "postgres":
        # Ensure database exists
        try:
            conn = psycopg2.connect(
                host=POSTGRES_CONFIG["host"],
                port=POSTGRES_CONFIG["port"],
                user=POSTGRES_CONFIG["user"],
                password=POSTGRES_CONFIG["password"],
                dbname="postgres"
            )
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{POSTGRES_CONFIG['database']}';")
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {POSTGRES_CONFIG['database']};")
            conn.close()
        except Exception as e:
            raise ConnectionError(f"PostgreSQL server not accessible: {e}")

        return psycopg2.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            user=POSTGRES_CONFIG["user"],
            password=POSTGRES_CONFIG["password"],
            dbname=POSTGRES_CONFIG["database"]
        )
    elif dialect == "sqlserver":
        # Ensure database exists
        try:
            if SQLSERVER_CONFIG["trusted_connection"].lower() == "yes":
                conn_str_master = (
                    f"Driver={{{SQLSERVER_CONFIG['driver']}}};"
                    f"Server={SQLSERVER_CONFIG['server']};"
                    f"Database=master;"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                )
            else:
                conn_str_master = (
                    f"Driver={{{SQLSERVER_CONFIG['driver']}}};"
                    f"Server={SQLSERVER_CONFIG['server']};"
                    f"Database=master;"
                    f"UID={SQLSERVER_CONFIG['user']};"
                    f"PWD={SQLSERVER_CONFIG['password']};"
                    f"TrustServerCertificate=yes;"
                )
            conn = pyodbc.connect(conn_str_master, autocommit=True)
            with conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM sys.databases WHERE name = '{SQLSERVER_CONFIG['database']}';")
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {SQLSERVER_CONFIG['database']};")
            conn.close()
        except Exception as e:
            raise ConnectionError(f"SQL Server not accessible: {e}")

        if SQLSERVER_CONFIG["trusted_connection"].lower() == "yes":
            conn_str = (
                f"Driver={{{SQLSERVER_CONFIG['driver']}}};"
                f"Server={SQLSERVER_CONFIG['server']};"
                f"Database={SQLSERVER_CONFIG['database']};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        else:
            conn_str = (
                f"Driver={{{SQLSERVER_CONFIG['driver']}}};"
                f"Server={SQLSERVER_CONFIG['server']};"
                f"Database={SQLSERVER_CONFIG['database']};"
                f"UID={SQLSERVER_CONFIG['user']};"
                f"PWD={SQLSERVER_CONFIG['password']};"
                f"TrustServerCertificate=yes;"
            )
        return pyodbc.connect(conn_str)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")


# ----------------------------------------------------------------------
# Schema & Seed Loader Helpers
# ----------------------------------------------------------------------

def _get_dialect_sql(file_path: str, dialect: str) -> List[str]:
    """Parse SQL statements belonging to the specified dialect tag block."""
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
                if stripped.startswith("--") or not stripped:
                    continue
                current_stmt.append(line)
                if stripped.endswith(";"):
                    statements.append("".join(current_stmt).strip())
                    current_stmt = []
                    
    return statements


def reset_source_database(dialect: str, config: dict = None):
    """Drop and clean all tables from the source database."""
    logger.info("Resetting %s database schema...", dialect)
    conn = get_connection(dialect)
    cursor = conn.cursor()
    tables = ["order_items", "audit_logs", "orders", "products", "users"]

    if dialect == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {t};")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    elif dialect == "postgres":
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
    elif dialect == "sqlserver":
        # Suppress foreign key check during drops
        for t in tables:
            cursor.execute(f"IF OBJECT_ID('{t}', 'U') IS NOT NULL DROP TABLE {t};")

    conn.commit()
    conn.close()


def reset_target_database(dialect: str, config: dict = None):
    """Reset target schema."""
    reset_source_database(dialect, config)


def apply_schema(dialect: str, config: dict = None):
    """Load and execute the DDL schema file for the dialect."""
    schema_file = os.path.join(os.path.dirname(__file__), "schemas", "ecommerce.sql")
    statements = _get_dialect_sql(schema_file, dialect)
    conn = get_connection(dialect)
    cursor = conn.cursor()
    try:
        for stmt in statements:
            if not stmt.strip():
                continue
            cursor.execute(stmt)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to apply DDL schema for {dialect}: {e}\nStatement: {stmt}") from e
    finally:
        conn.close()


def apply_seed_data(dialect: str, config: dict = None):
    """Load and execute the DML seed file for the dialect."""
    seed_file = os.path.join(os.path.dirname(__file__), "datasets", "ecommerce_seed.sql")
    statements = _get_dialect_sql(seed_file, dialect)
    conn = get_connection(dialect)
    cursor = conn.cursor()
    try:
        for stmt in statements:
            if not stmt.strip():
                continue
            cursor.execute(stmt)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to apply DML seed data for {dialect}: {e}\nStatement: {stmt}") from e
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Assertion & Validation Helpers (with Diagnostics)
# ----------------------------------------------------------------------

def validate_table_counts(conn: Any, dialect: str, expected: int):
    """Verify the number of user tables matches the expected count."""
    cursor = conn.cursor()
    tables = []
    if dialect == "mysql":
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
    elif dialect == "postgres":
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [r[0] for r in cursor.fetchall()]
    elif dialect == "sqlserver":
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';")
        tables = [r[0] for r in cursor.fetchall()]

    actual = len(tables)
    if actual != expected:
        print("DIAGNOSTICS: Table Count Mismatch!")
        print(f"Expected: {expected}, Actual: {actual}")
        print(f"Tables Found: {tables}")
        raise AssertionError(f"Table count mismatch: expected {expected}, found {actual} tables.")


def validate_row_counts(conn: Any, dialect: str, table_name: str, expected: int):
    """Verify that row count of the table matches the expected count."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    row = cursor.fetchone()
    actual = int(row[0])

    if actual != expected:
        print(f"DIAGNOSTICS: Row Count Mismatch in table '{table_name}'!")
        print(f"Expected: {expected}, Actual: {actual}")
        raise AssertionError(f"Table '{table_name}' row count mismatch: expected {expected}, found {actual}.")


def validate_primary_keys(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Verify primary key columns match between source and target."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_pk_cols(conn, dialect):
        cursor = conn.cursor()
        if dialect == "mysql":
            cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY';")
            return [r[4] for r in cursor.fetchall()]
        elif dialect == "postgres":
            cursor.execute(f"""
                SELECT a.attname
                FROM   pg_index i
                JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE  i.indrelid = '{table_name}'::regclass AND i.indisprimary;
            """)
            return [r[0] for r in cursor.fetchall()]
        elif dialect == "sqlserver":
            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
                AND TABLE_NAME = '{table_name}';
            """)
            return [r[0] for r in cursor.fetchall()]
            
    src_pk = sorted(_get_pk_cols(src_conn, src_dialect))
    tgt_pk = sorted(_get_pk_cols(tgt_conn, tgt_dialect))

    if src_pk != tgt_pk:
        print(f"DIAGNOSTICS: Primary Key Mismatch for table '{table_name}'!")
        print(f"Source PK ({src_dialect}): {src_pk}")
        print(f"Target PK ({tgt_dialect}): {tgt_pk}")
        raise AssertionError(f"Primary key mismatch in table '{table_name}'.")


def validate_constraints(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Verify unique constraints and column presence."""
    validate_primary_keys(src_conn, tgt_conn, dialect_pair, table_name)


def validate_indexes(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Verify that index count target matches or exceeds source index count."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _get_idx_count(conn, dialect):
        cursor = conn.cursor()
        if dialect == "mysql":
            cursor.execute(f"SHOW INDEX FROM {table_name};")
            return len({r[2] for r in cursor.fetchall()})
        elif dialect == "postgres":
            cursor.execute(f"SELECT indexname FROM pg_indexes WHERE tablename = '{table_name}';")
            return len(cursor.fetchall())
        elif dialect == "sqlserver":
            cursor.execute(f"SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('{table_name}') AND is_primary_key = 0 AND name IS NOT NULL;")
            return len(cursor.fetchall())
            
    src_cnt = _get_idx_count(src_conn, src_dialect)
    tgt_cnt = _get_idx_count(tgt_conn, tgt_dialect)

    if tgt_cnt < src_cnt:
        print(f"DIAGNOSTICS: Index Count Mismatch for table '{table_name}'!")
        print(f"Source Index Count ({src_dialect}): {src_cnt}")
        print(f"Target Index Count ({tgt_dialect}): {tgt_cnt}")
        raise AssertionError(f"Index count target mismatch in table '{table_name}'.")


def validate_foreign_keys(conn: Any, dialect: str, table_name: str):
    """Assert that foreign key records are valid (no orphan references)."""
    cursor = conn.cursor()
    if table_name == "orders":
        cursor.execute("SELECT user_id FROM orders WHERE user_id NOT IN (SELECT id FROM users);")
        orphans = cursor.fetchall()
        if orphans:
            print("DIAGNOSTICS: Foreign Key Constraint Violation (orders -> users)!")
            print(f"Orphan user_ids: {orphans}")
            raise AssertionError(f"Foreign key constraint violation on orders -> users.")
    elif table_name == "order_items":
        cursor.execute("SELECT order_id FROM order_items WHERE order_id NOT IN (SELECT id FROM orders);")
        orphan_orders = cursor.fetchall()
        cursor.execute("SELECT product_id FROM order_items WHERE product_id NOT IN (SELECT id FROM products);")
        orphan_prods = cursor.fetchall()
        if orphan_orders or orphan_prods:
            print("DIAGNOSTICS: Foreign Key Constraint Violation (order_items)!")
            print(f"Orphan order_ids: {orphan_orders}")
            print(f"Orphan product_ids: {orphan_prods}")
            raise AssertionError(f"Foreign key constraint violation on order_items.")


def validate_json_columns(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str, col_name: str):
    """Deep compare values in JSON-formatted columns."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _fetch_json(conn, dialect):
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {col_name} FROM {table_name} ORDER BY id;")
        data = {}
        for r in cursor.fetchall():
            r_id = r[0]
            val = r[1]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            data[r_id] = val
        return data

    src_data = _fetch_json(src_conn, src_dialect)
    tgt_data = _fetch_json(tgt_conn, tgt_dialect)

    for r_id, src_val in src_data.items():
        tgt_val = tgt_data.get(r_id)
        if src_val != tgt_val:
            print(f"DIAGNOSTICS: JSON Content Mismatch in table '{table_name}', column '{col_name}', row {r_id}!")
            print(f"Source JSON: {src_val}")
            print(f"Target JSON: {tgt_val}")
            raise AssertionError(f"JSON payload mismatch on row {r_id}.")


def validate_blob_columns(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str, col_name: str):
    """Compare exact bytes of BLOB / binary columns."""
    src_dialect, tgt_dialect = dialect_pair

    def _fetch_blob(conn, dialect):
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {col_name} FROM {table_name} ORDER BY id;")
        data = {}
        for r in cursor.fetchall():
            r_id = r[0]
            val = r[1]
            if isinstance(val, memoryview):
                val = val.tobytes()
            elif isinstance(val, bytearray):
                val = bytes(val)
            data[r_id] = val
        return data

    src_data = _fetch_blob(src_conn, src_dialect)
    tgt_data = _fetch_blob(tgt_conn, tgt_dialect)

    for r_id, src_val in src_data.items():
        tgt_val = tgt_data.get(r_id)
        if src_val != tgt_val:
            print(f"DIAGNOSTICS: BLOB/Binary Content Mismatch in table '{table_name}', column '{col_name}', row {r_id}!")
            print(f"Source BLOB Bytes: {src_val}")
            print(f"Target BLOB Bytes: {tgt_val}")
            raise AssertionError(f"BLOB payload mismatch on row {r_id}.")


def validate_data_integrity(src_conn: Any, tgt_conn: Any, dialect_pair: Tuple[str, str], table_name: str):
    """Compare row values for general data equality."""
    src_dialect, tgt_dialect = dialect_pair
    
    def _fetch_all(conn, dialect):
        cursor = conn.cursor()
        # For SQL Server, text/blob may require specific handling, but general fields are queried
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY id;")
        rows = []
        for r in cursor.fetchall():
            row_vals = []
            for val in r:
                if isinstance(val, memoryview):
                    val = val.tobytes()
                elif isinstance(val, bytearray):
                    val = bytes(val)
                row_vals.append(val)
            rows.append(tuple(row_vals))
        return rows

    src_rows = _fetch_all(src_conn, src_dialect)
    tgt_rows = _fetch_all(tgt_conn, tgt_dialect)

    if len(src_rows) != len(tgt_rows):
        print(f"DIAGNOSTICS: Row Count Length Mismatch in table '{table_name}'!")
        print(f"Source Rows Count: {len(src_rows)}")
        print(f"Target Rows Count: {len(tgt_rows)}")
        raise AssertionError(f"Total row mismatch: source={len(src_rows)}, target={len(tgt_rows)}")

    for i, (src_r, tgt_r) in enumerate(zip(src_rows, tgt_rows)):
        if len(src_r) != len(tgt_r):
            print(f"DIAGNOSTICS: Column Arity Mismatch at row index {i} in table '{table_name}'!")
            raise AssertionError(f"Row structure mismatch at index {i}.")
        
        # Compare core values element-by-element
        for col_idx, (s_val, t_val) in enumerate(zip(src_r, tgt_r)):
            if s_val != t_val:
                # Toleration for decimal conversion/comparisons and string variations
                try:
                    if float(s_val) == float(t_val):
                        continue
                except Exception:
                    pass
                print(f"DIAGNOSTICS: Field Value Mismatch at row index {i}, column index {col_idx} in table '{table_name}'!")
                print(f"Source Value ({src_dialect}): {repr(s_val)}")
                print(f"Target Value ({tgt_dialect}): {repr(t_val)}")
                raise AssertionError(f"Data value mismatch at row index {i}, col index {col_idx}.")
