"""
P2 Real Physical SQLite Integration Test Suite
===============================================
Performs real file-based physical I/O validation against local SQLite database files:
- Identical databases (PASS)
- Same count, different row data (FAIL)
- NULL mismatch (FAIL)
- Empty identical tables (PASS)
- Unicode data matching (PASS)
- Deterministic checksum restart verification (PASS)
"""

import unittest
import sqlite3
import tempfile
import os
import asyncio
import types

from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter
from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum


def _make_sqlite_config(db_path: str):
    """Create a minimal SQLiteAdapter config namespace pointing to a real file."""
    return types.SimpleNamespace(
        database_name=db_path,
        mock_mode=False,
        extra={},
        host='',
        port=None,
        username=None,
        password=None,
        database=db_path,
    )


class TestP2SQLiteRealPhysicalIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.src_db_path = os.path.join(self.tmp_dir.name, "source.db")
        self.tgt_db_path = os.path.join(self.tmp_dir.name, "target.db")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_db(self, path: str, sql_statements: list):
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        for stmt in sql_statements:
            cur.execute(stmt)
        conn.commit()
        conn.close()

    def test_01_identical_databases_produce_identical_canonical_checksum(self):
        """Scenario 1: Identical database files must produce 100% identical canonical checksums."""
        schema_sql = "CREATE TABLE users (id INT PRIMARY KEY, name TEXT, balance REAL)"
        data_sql = [
            "INSERT INTO users VALUES (1, 'Alice', 100.50)",
            "INSERT INTO users VALUES (2, 'Bob', 250.75)"
        ]
        self._create_db(self.src_db_path, [schema_sql] + data_sql)
        self._create_db(self.tgt_db_path, [schema_sql] + data_sql)

        src_adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
        tgt_adapter = SQLiteAdapter(_make_sqlite_config(self.tgt_db_path))

        async def _run():
            await src_adapter.connect()
            await tgt_adapter.connect()
            src_cs = await src_adapter.compute_checksum("users")
            tgt_cs = await tgt_adapter.compute_checksum("users")
            await src_adapter.close()
            await tgt_adapter.close()
            return src_cs, tgt_cs

        src_cs, tgt_cs = asyncio.run(_run())
        self.assertEqual(src_cs, tgt_cs)
        # Prove it's a real SHA-256 hex string, not "mock_checksum"
        self.assertNotEqual(src_cs, "mock_checksum")
        self.assertEqual(len(src_cs), 64)

    def test_02_same_count_different_data_detected(self):
        """Scenario 2: Same row count with corrupt value (Bob vs Eve) MUST produce different checksums."""
        schema_sql = "CREATE TABLE users (id INT PRIMARY KEY, name TEXT)"
        src_data = ["INSERT INTO users VALUES (1, 'Alice')", "INSERT INTO users VALUES (2, 'Bob')"]
        tgt_data = ["INSERT INTO users VALUES (1, 'Alice')", "INSERT INTO users VALUES (2, 'Eve')"]

        self._create_db(self.src_db_path, [schema_sql] + src_data)
        self._create_db(self.tgt_db_path, [schema_sql] + tgt_data)

        src_adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
        tgt_adapter = SQLiteAdapter(_make_sqlite_config(self.tgt_db_path))

        async def _run():
            await src_adapter.connect()
            await tgt_adapter.connect()
            src_cs = await src_adapter.compute_checksum("users")
            tgt_cs = await tgt_adapter.compute_checksum("users")
            await src_adapter.close()
            await tgt_adapter.close()
            return src_cs, tgt_cs

        src_cs, tgt_cs = asyncio.run(_run())
        # Both DBs have 2 rows; checksums MUST differ because Bob != Eve
        self.assertNotEqual(src_cs, tgt_cs)

    def test_03_null_mismatch_detected(self):
        """Scenario 3: NULL vs non-NULL value (NULL vs '') MUST produce different checksums."""
        schema_sql = "CREATE TABLE test_null (id INT PRIMARY KEY, email TEXT)"
        src_data = ["INSERT INTO test_null VALUES (1, NULL)"]
        tgt_data = ["INSERT INTO test_null VALUES (1, '')"]

        self._create_db(self.src_db_path, [schema_sql] + src_data)
        self._create_db(self.tgt_db_path, [schema_sql] + tgt_data)

        src_adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
        tgt_adapter = SQLiteAdapter(_make_sqlite_config(self.tgt_db_path))

        async def _run():
            await src_adapter.connect()
            await tgt_adapter.connect()
            src_cs = await src_adapter.compute_checksum("test_null")
            tgt_cs = await tgt_adapter.compute_checksum("test_null")
            await src_adapter.close()
            await tgt_adapter.close()
            return src_cs, tgt_cs

        src_cs, tgt_cs = asyncio.run(_run())
        self.assertNotEqual(src_cs, tgt_cs)

    def test_04_empty_identical_tables_match(self):
        """Scenario 4: Two physically empty tables produce matching checksums."""
        schema_sql = "CREATE TABLE empty_tbl (id INT PRIMARY KEY, val TEXT)"
        self._create_db(self.src_db_path, [schema_sql])
        self._create_db(self.tgt_db_path, [schema_sql])

        src_adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
        tgt_adapter = SQLiteAdapter(_make_sqlite_config(self.tgt_db_path))

        async def _run():
            await src_adapter.connect()
            await tgt_adapter.connect()
            src_cs = await src_adapter.compute_checksum("empty_tbl")
            tgt_cs = await tgt_adapter.compute_checksum("empty_tbl")
            await src_adapter.close()
            await tgt_adapter.close()
            return src_cs, tgt_cs

        src_cs, tgt_cs = asyncio.run(_run())
        self.assertEqual(src_cs, tgt_cs)
        # Empty table canonical sentinel
        import hashlib
        self.assertEqual(src_cs, hashlib.sha256(b"EMPTY_TABLE").hexdigest())

    def test_05_unicode_data_handling(self):
        """Scenario 5: Unicode UTF-8 string matching across SQLite files."""
        schema_sql = "CREATE TABLE unicode_tbl (id INT PRIMARY KEY, text_val TEXT)"
        data_sql = ["INSERT INTO unicode_tbl VALUES (1, 'Akaal-ਆਕਾਲ-मैल')"]
        self._create_db(self.src_db_path, [schema_sql] + data_sql)
        self._create_db(self.tgt_db_path, [schema_sql] + data_sql)

        src_adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
        tgt_adapter = SQLiteAdapter(_make_sqlite_config(self.tgt_db_path))

        async def _run():
            await src_adapter.connect()
            await tgt_adapter.connect()
            src_cs = await src_adapter.compute_checksum("unicode_tbl")
            tgt_cs = await tgt_adapter.compute_checksum("unicode_tbl")
            await src_adapter.close()
            await tgt_adapter.close()
            return src_cs, tgt_cs

        src_cs, tgt_cs = asyncio.run(_run())
        self.assertEqual(src_cs, tgt_cs)

    def test_06_deterministic_checksum_restart(self):
        """Scenario 6: Same physical data produces identical checksum across two independent computations."""
        schema_sql = "CREATE TABLE items (id INT PRIMARY KEY, label TEXT, value REAL)"
        data_sql = [
            "INSERT INTO items VALUES (1, 'X', 3.14)",
            "INSERT INTO items VALUES (2, 'Y', 2.71)",
        ]
        self._create_db(self.src_db_path, [schema_sql] + data_sql)

        async def _run_once():
            adapter = SQLiteAdapter(_make_sqlite_config(self.src_db_path))
            await adapter.connect()
            cs = await adapter.compute_checksum("items")
            await adapter.close()
            return cs

        cs_first = asyncio.run(_run_once())
        cs_second = asyncio.run(_run_once())
        self.assertEqual(cs_first, cs_second)


if __name__ == "__main__":
    unittest.main()
