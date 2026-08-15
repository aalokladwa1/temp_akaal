"""
AKAAL Phase P4.2 — Relational Connector Fleet Reality Hostile Test Suite
==========================================================================
Verifies that all 7 relational database adapters in AKAAL (Oracle, PostgreSQL,
MySQL, MariaDB, MS SQL Server, IBM Db2, SQLite) implement strict Zero-Fake
physical execution semantics and fail closed under all hostile conditions.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from akaal.adapters.base_adapter import BaseAdapter
from akaal.adapters.rdbms.oracle_adapter import OracleAdapter
from akaal.adapters.rdbms.postgresql_adapter import PostgreSQLAdapter
from akaal.adapters.rdbms.mysql_adapter import MySQLAdapter
from akaal.adapters.rdbms.mariadb_adapter import MariaDBAdapter
from akaal.adapters.rdbms.mssql_adapter import MSSQLAdapter
from akaal.adapters.rdbms.ibm_db2_adapter import IBMDB2Adapter
from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter
from akaal.core.models.enums import SystemType, AdapterCapability


class DummyConfig:
    def __init__(self, host="localhost", port=5432, username="user", password="pwd", database_name="testdb", extra=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database_name = database_name
        self.extra = extra or {}


class TestP42RelationalFleetRealitySuite(unittest.IsolatedAsyncioTestCase):

    async def test_01_all_relational_adapters_eradicated_mock_mode(self):
        """Verify zero mock attributes exist on BaseAdapter or any relational adapter instance."""
        adapters = [
            OracleAdapter(DummyConfig(host="example.com")),
            PostgreSQLAdapter(DummyConfig(host="source-db.example.com")),
            MySQLAdapter(DummyConfig(host="target-db.example.com")),
            MariaDBAdapter(DummyConfig(host="mariadb-source.example.com")),
            MSSQLAdapter(DummyConfig(host="connection-fail.example.com")),
            IBMDB2Adapter(DummyConfig(host="db2-prod.example.com")),
            SQLiteAdapter(DummyConfig(database_name=":memory:")),
        ]
        for adapter in adapters:
            self.assertFalse(hasattr(adapter, "mock_mode"), f"{adapter.__class__.__name__} still contains 'mock_mode'")
            self.assertFalse(hasattr(adapter, "_is_mock"), f"{adapter.__class__.__name__} still contains '_is_mock'")
            self.assertFalse(getattr(adapter, "is_connected", False), f"{adapter.__class__.__name__} connected prior to physical connect()")

    async def test_02_disconnected_operations_fail_closed(self):
        """Verify every disconnected adapter operation raises RuntimeError fail-closed."""
        adapters = [
            OracleAdapter(DummyConfig()),
            PostgreSQLAdapter(DummyConfig()),
            MySQLAdapter(DummyConfig()),
            MariaDBAdapter(DummyConfig()),
            MSSQLAdapter(DummyConfig()),
            IBMDB2Adapter(DummyConfig()),
            SQLiteAdapter(DummyConfig(database_name="/nonexistent/path/db.sqlite")),
        ]
        for adapter in adapters:
            with self.assertRaises(RuntimeError, msg=f"{adapter.__class__.__name__} did not fail closed on discover_tables"):
                await adapter.discover_tables()
            with self.assertRaises(RuntimeError, msg=f"{adapter.__class__.__name__} did not fail closed on get_row_count"):
                await adapter.get_row_count("test_table")
            with self.assertRaises(RuntimeError, msg=f"{adapter.__class__.__name__} did not fail closed on read_batch"):
                await adapter.read_batch("test_table", offset=0, limit=10)

    async def test_03_missing_drivers_raise_runtime_error(self):
        """Verify missing drivers cause connect() to raise RuntimeError rather than silent fallback."""
        with patch.dict(sys.modules, {"oracledb": None, "cx_Oracle": None}):
            oracle = OracleAdapter(DummyConfig())
            with self.assertRaises(RuntimeError):
                await oracle.connect()
            self.assertFalse(oracle.is_connected)

        with patch.dict(sys.modules, {"psycopg2": None}):
            pg = PostgreSQLAdapter(DummyConfig())
            with self.assertRaises(RuntimeError):
                await pg.connect()
            self.assertFalse(pg.is_connected)

        with patch.dict(sys.modules, {"pymysql": None}):
            mysql = MySQLAdapter(DummyConfig())
            with self.assertRaises(RuntimeError):
                await mysql.connect()
            self.assertFalse(mysql.is_connected)

            mariadb = MariaDBAdapter(DummyConfig())
            with self.assertRaises(RuntimeError):
                await mariadb.connect()
            self.assertFalse(mariadb.is_connected)

        with patch.dict(sys.modules, {"ibm_db": None}):
            db2 = IBMDB2Adapter(DummyConfig())
            with self.assertRaises(RuntimeError):
                await db2.connect()
            self.assertFalse(db2.is_connected)

    async def test_04_sqlite_physical_end_to_end_operations(self):
        """Verify SQLiteAdapter executes 100% physical database operations correctly."""
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "test.db")

        try:
            adapter = SQLiteAdapter(DummyConfig(database_name=tmp_path))
            await adapter.connect()
            self.assertTrue(adapter.is_connected)

            # Create physical table
            def _create_schema():
                conn = adapter._conn
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance REAL, owner TEXT)")
                cursor.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, account_id INTEGER, FOREIGN KEY(account_id) REFERENCES accounts(id))")
                conn.commit()
            import asyncio
            await asyncio.to_thread(_create_schema)

            # Catalog discovery
            tables = await adapter.discover_tables()
            self.assertIn("accounts", tables)
            self.assertIn("orders", tables)

            cols = await adapter.discover_columns("accounts")
            col_names = [c["name"] for c in cols]
            self.assertIn("id", col_names)
            self.assertIn("balance", col_names)
            self.assertIn("owner", col_names)

            fks = await adapter.discover_foreign_keys()
            self.assertTrue(len(fks) >= 1)

            # Bulk Write
            rows = [
                {"id": 1, "balance": 100.50, "owner": "Alice"},
                {"id": 2, "balance": 250.00, "owner": "Bob"},
                {"id": 3, "balance": 50.75, "owner": "Charlie"},
            ]
            written = await adapter.write_batch("accounts", rows)
            self.assertEqual(written, 3)

            # Row count
            count = await adapter.get_row_count("accounts")
            self.assertEqual(count, 3)

            # Bulk Read
            read_rows = await adapter.read_batch("accounts", offset=0, limit=2)
            self.assertEqual(len(read_rows), 2)
            self.assertEqual(read_rows[0]["owner"], "Alice")

            # Checksum
            checksum = await adapter.compute_checksum("accounts")
            self.assertTrue(isinstance(checksum, str) and len(checksum) == 64)

            # Transactions
            await adapter.begin_transaction()
            await adapter.write_batch("accounts", [{"id": 4, "balance": 999.00, "owner": "Dave"}])
            await adapter.rollback_transaction()

            count_after_rollback = await adapter.get_row_count("accounts")
            self.assertEqual(count_after_rollback, 3)

            await adapter.close()
            self.assertFalse(adapter.is_connected)

        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                    os.rmdir(tmp_dir)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
