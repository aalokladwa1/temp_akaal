import os
import tempfile
import unittest
from akaal.migration.execution.incremental.store import MemoryStateStore, SQLiteStateStore, PostgreSQLStateStore

class TestIncrementalStore(unittest.TestCase):
    async def run_memory_store(self):
        store = MemoryStateStore()
        await store.save_watermark("p1", "m1", "t1", "2026-01-01")
        val = await store.get_watermark("p1", "m1", "t1")
        self.assertEqual(val, "2026-01-01")

        val_none = await store.get_watermark("p1", "m1", "t2")
        self.assertIsNone(val_none)

    async def run_sqlite_store(self):
        # Create temp file path
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            store = SQLiteStateStore(path)
            await store.save_watermark("p1", "m1", "t1", "100")
            val = await store.get_watermark("p1", "m1", "t1")
            self.assertEqual(val, "100")
        finally:
            if os.path.exists(path):
                os.remove(path)

    async def run_postgres_store(self):
        store = PostgreSQLStateStore({"host": "localhost"})
        await store.save_watermark("p2", "m2", "t2", "2026-07-17")
        val = await store.get_watermark("p2", "m2", "t2")
        self.assertEqual(val, "2026-07-17")

    def test_run_async(self):
        # Bridge to run the async tests in unittest loop
        import asyncio
        asyncio.run(self.run_memory_store())
        asyncio.run(self.run_sqlite_store())
        asyncio.run(self.run_postgres_store())
