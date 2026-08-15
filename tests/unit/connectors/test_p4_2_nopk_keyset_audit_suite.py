"""
AKAAL P4.2 — Hostile No-Primary-Key Keyset & Pagination Audit Suite.
===================================================================
Forensic verification of primary key, composite primary key, unique key fallback,
and truthful capability degradation for tables lacking primary/unique keys.
"""

import unittest
import asyncio
import tempfile
import os
import sqlite3
from typing import Dict, Any, List

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig
from akaal.adapters.rdbms.sqlite_adapter import SQLiteAdapter


class TestP42NoPKKeysetAuditSuite(unittest.TestCase):
    """Hostile test suite for no-PK tables, duplicate column values, reconnect, and composite PKs."""

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self) -> None:
        self.loop.close()

    def test_01_composite_primary_key_keyset_pagination(self):
        """01: Composite PK tables execute strict lexicographical keyset pagination."""
        async def run():
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                cfg = ConnectionConfig(
                    system_type=SystemType.SQLITE,
                    host="localhost",
                    port=0,
                    database_name=tmp_path,
                    credentials_ref="none",
                )
                adapter = SQLiteAdapter(cfg)
                await adapter.connect()

                def _init():
                    c = adapter._conn.cursor()
                    c.execute("CREATE TABLE composite_test (tenant_id INT, user_id INT, name TEXT, PRIMARY KEY (tenant_id, user_id))")
                    c.execute("INSERT INTO composite_test VALUES (1, 100, 'A')")
                    c.execute("INSERT INTO composite_test VALUES (1, 101, 'B')")
                    c.execute("INSERT INTO composite_test VALUES (2, 100, 'C')")
                    c.execute("INSERT INTO composite_test VALUES (2, 105, 'D')")
                    adapter._conn.commit()
                await asyncio.to_thread(_init)

                # Batch 1 (limit 2)
                batch1 = await adapter.read_batch("composite_test", offset=0, limit=2)
                self.assertEqual(len(batch1), 2)
                self.assertEqual(batch1[0]["tenant_id"], 1)
                self.assertEqual(batch1[0]["user_id"], 100)

                # Resume using last_processed_primary_key of last item in batch1 (tenant_id=1, user_id=101)
                last_pk = {"tenant_id": batch1[-1]["tenant_id"], "user_id": batch1[-1]["user_id"]}
                batch2 = await adapter.read_batch("composite_test", offset=0, limit=2, last_processed_primary_key=last_pk)
                self.assertEqual(len(batch2), 2)
                self.assertEqual(batch2[0]["tenant_id"], 2)
                self.assertEqual(batch2[0]["user_id"], 100)

                await adapter.close()
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        self.loop.run_until_complete(run())

    def test_02_unique_key_fallback_pagination(self):
        """02: Tables without PK but with UNIQUE non-null constraint use unique key keyset pagination."""
        async def run():
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                cfg = ConnectionConfig(
                    system_type=SystemType.SQLITE,
                    host="localhost",
                    port=0,
                    database_name=tmp_path,
                    credentials_ref="none",
                )
                adapter = SQLiteAdapter(cfg)
                await adapter.connect()

                def _init():
                    c = adapter._conn.cursor()
                    c.execute("CREATE TABLE unique_test (email TEXT UNIQUE NOT NULL, name TEXT)")
                    c.execute("INSERT INTO unique_test VALUES ('a@ex.com', 'A')")
                    c.execute("INSERT INTO unique_test VALUES ('b@ex.com', 'B')")
                    c.execute("INSERT INTO unique_test VALUES ('c@ex.com', 'C')")
                    adapter._conn.commit()
                await asyncio.to_thread(_init)

                batch1 = await adapter.read_batch("unique_test", offset=0, limit=2)
                self.assertEqual(len(batch1), 2)
                self.assertEqual(batch1[0]["email"], "a@ex.com")

                last_pk = {"email": batch1[-1]["email"]}
                batch2 = await adapter.read_batch("unique_test", offset=0, limit=2, last_processed_primary_key=last_pk)
                self.assertEqual(len(batch2), 1)
                self.assertEqual(batch2[0]["email"], "c@ex.com")

                await adapter.close()
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        self.loop.run_until_complete(run())

    def test_03_no_pk_duplicate_first_column_values(self):
        """03: Tables without PK or UNIQUE keys return empty _unique_key_columns and do NOT invent 'id'."""
        async def run():
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                cfg = ConnectionConfig(
                    system_type=SystemType.SQLITE,
                    host="localhost",
                    port=0,
                    database_name=tmp_path,
                    credentials_ref="none",
                )
                adapter = SQLiteAdapter(cfg)
                await adapter.connect()

                def _init():
                    c = adapter._conn.cursor()
                    c.execute("CREATE TABLE nopk_test (category TEXT, val INT)")
                    c.execute("INSERT INTO nopk_test VALUES ('SAME', 1)")
                    c.execute("INSERT INTO nopk_test VALUES ('SAME', 2)")
                    c.execute("INSERT INTO nopk_test VALUES ('SAME', 3)")
                    c.execute("INSERT INTO nopk_test VALUES ('SAME', 4)")
                    adapter._conn.commit()
                await asyncio.to_thread(_init)

                # Verify no PK or unique columns exist
                pks = await adapter._primary_key_columns("nopk_test")
                uniques = await adapter._unique_key_columns("nopk_test")
                self.assertEqual(pks, [])
                self.assertEqual(uniques, [])

                # Verify read_batch completes without error (does not reference non-existent 'id')
                batch1 = await adapter.read_batch("nopk_test", offset=0, limit=2)
                self.assertEqual(len(batch1), 2)

                batch2 = await adapter.read_batch("nopk_test", offset=2, limit=2)
                self.assertEqual(len(batch2), 2)

                await adapter.close()
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        self.loop.run_until_complete(run())

    def test_04_inserts_and_deletes_between_batches(self):
        """04: Inserts/Deletes between batches are handled correctly by PK keyset pagination."""
        async def run():
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                cfg = ConnectionConfig(
                    system_type=SystemType.SQLITE,
                    host="localhost",
                    port=0,
                    database_name=tmp_path,
                    credentials_ref="none",
                )
                adapter = SQLiteAdapter(cfg)
                await adapter.connect()

                def _init():
                    c = adapter._conn.cursor()
                    c.execute("CREATE TABLE cdc_dml_test (id INT PRIMARY KEY, val TEXT)")
                    c.execute("INSERT INTO cdc_dml_test VALUES (1, 'v1')")
                    c.execute("INSERT INTO cdc_dml_test VALUES (2, 'v2')")
                    c.execute("INSERT INTO cdc_dml_test VALUES (5, 'v5')")
                    adapter._conn.commit()
                await asyncio.to_thread(_init)

                batch1 = await adapter.read_batch("cdc_dml_test", offset=0, limit=2)
                self.assertEqual(len(batch1), 2)
                self.assertEqual(batch1[-1]["id"], 2)

                # Perform concurrent DML: insert id=3 and delete id=5
                def _dml():
                    c = adapter._conn.cursor()
                    c.execute("INSERT INTO cdc_dml_test VALUES (3, 'v3')")
                    c.execute("DELETE FROM cdc_dml_test WHERE id = 5")
                    adapter._conn.commit()
                await asyncio.to_thread(_dml)

                # Resume keyset pagination from id=2
                last_pk = {"id": 2}
                batch2 = await adapter.read_batch("cdc_dml_test", offset=0, limit=5, last_processed_primary_key=last_pk)
                self.assertEqual(len(batch2), 1)
                self.assertEqual(batch2[0]["id"], 3)

                await adapter.close()
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
