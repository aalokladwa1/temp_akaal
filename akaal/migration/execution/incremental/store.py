import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class IncrementalStateStore(ABC):
    @abstractmethod
    async def get_watermark(self, project_id: str, migration_id: str, table_name: str) -> Optional[Any]:
        """Retrieve the watermark for a table."""
        pass

    @abstractmethod
    async def save_watermark(self, project_id: str, migration_id: str, table_name: str, watermark: Any) -> None:
        """Persist the watermark for a table."""
        pass

class MemoryStateStore(IncrementalStateStore):
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    async def get_watermark(self, project_id: str, migration_id: str, table_name: str) -> Optional[Any]:
        key = f"{project_id}:{migration_id}:{table_name}"
        return self._store.get(key)

    async def save_watermark(self, project_id: str, migration_id: str, table_name: str, watermark: Any) -> None:
        key = f"{project_id}:{migration_id}:{table_name}"
        self._store[key] = watermark

class SQLiteStateStore(IncrementalStateStore):
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._initialized = False

    def _init_db(self):
        if self._initialized:
            return
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watermarks (
                    project_id TEXT,
                    migration_id TEXT,
                    table_name TEXT,
                    watermark TEXT,
                    updated_at REAL,
                    PRIMARY KEY (project_id, migration_id, table_name)
                )
            """)
        conn.close()
        self._initialized = True

    async def get_watermark(self, project_id: str, migration_id: str, table_name: str) -> Optional[Any]:
        self._init_db()
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT watermark FROM watermarks WHERE project_id=? AND migration_id=? AND table_name=?",
            (project_id, migration_id, table_name)
        )
        row = cursor.fetchone()
        val = row[0] if row else None
        conn.close()
        return val

    async def save_watermark(self, project_id: str, migration_id: str, table_name: str, watermark: Any) -> None:
        self._init_db()
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO watermarks (project_id, migration_id, table_name, watermark, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, migration_id, table_name, str(watermark), time.time())
            )
        conn.close()

class PostgreSQLStateStore(IncrementalStateStore):
    def __init__(self, connection_options: Dict[str, Any]) -> None:
        self.options = connection_options
        self._cache = MemoryStateStore()

    async def get_watermark(self, project_id: str, migration_id: str, table_name: str) -> Optional[Any]:
        # Emulates database lookups falling back to memory store cache
        return await self._cache.get_watermark(project_id, migration_id, table_name)

    async def save_watermark(self, project_id: str, migration_id: str, table_name: str, watermark: Any) -> None:
        await self._cache.save_watermark(project_id, migration_id, table_name, watermark)
