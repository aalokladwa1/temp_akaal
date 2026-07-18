"""
Akaal — Schema Inventory Model
==============================
Structured model for discovered database schemas, tables, columns, indexes, foreign keys.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ColumnMetadata:
    name: str
    data_type: str
    nullable: bool = True
    default_value: Any = None
    primary_key: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableMetadata:
    table_name: str
    schema_name: str = "public"
    columns: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SchemaInventory:
    """Discovered schema structures."""
    schemas: List[str] = field(default_factory=lambda: ["public"])
    tables: List[TableMetadata] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    views: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemas": self.schemas,
            "tables": [
                {
                    "table_name": t.table_name,
                    "schema_name": t.schema_name,
                    "columns": t.columns,
                    "indexes": t.indexes,
                    "constraints": t.constraints,
                }
                for t in self.tables
            ],
            "foreign_keys": self.foreign_keys,
            "views": self.views,
        }
