"""
AKAAL Database Capability Extension Contract (P4.1).
=====================================================
Defines relational and SQL database capability extension interfaces:
- Schema discovery (tables, columns, primary keys, foreign keys, indexes, constraints, views, procs, triggers, sequences)
- Bulk read/write and partitioned scan
- CDC log mining hooks and source position extraction
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IDatabaseCapability(ABC):
    """Extension contract for relational databases (Oracle, Postgres, MySQL, MSSQL, DB2, SQLite)."""

    @abstractmethod
    async def discover_schemas(self) -> List[str]:
        """Discovers database schema names."""
        pass

    @abstractmethod
    async def discover_tables(self, schema_name: Optional[str] = None) -> List[str]:
        """Discovers tables within schema."""
        pass

    @abstractmethod
    async def discover_columns(self, table_name: str, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers column definitions and data types."""
        pass

    @abstractmethod
    async def discover_primary_keys(self, table_name: str, schema_name: Optional[str] = None) -> List[str]:
        """Discovers primary key column names."""
        pass

    @abstractmethod
    async def discover_foreign_keys(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers foreign key relationships across schema."""
        pass

    @abstractmethod
    async def discover_indexes(self, table_name: str, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers table indexes."""
        pass

    @abstractmethod
    async def discover_constraints(self, table_name: str, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers unique, check, and not-null constraints."""
        pass

    @abstractmethod
    async def discover_views(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers view definitions."""
        pass

    @abstractmethod
    async def discover_routines(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers stored procedures, functions, and packages."""
        pass

    @abstractmethod
    async def discover_triggers(self, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers table triggers."""
        pass

    @abstractmethod
    async def discover_partitions(self, table_name: str, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discovers partition metadata."""
        pass

    @abstractmethod
    async def read_table_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        schema_name: Optional[str] = None,
        filter_clause: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Reads batch of rows from source table."""
        pass

    @abstractmethod
    async def write_table_batch(
        self,
        table_name: str,
        rows: List[Dict[str, Any]],
        schema_name: Optional[str] = None,
    ) -> int:
        """Writes batch of rows to target table. Returns number of rows written."""
        pass
