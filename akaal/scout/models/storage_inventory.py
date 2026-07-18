"""
Akaal — Storage Inventory Model
===============================
Structured model for discovered database storage sizes, tablespaces, partitions, row counts.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StorageInventory:
    """Discovered database storage statistics."""
    database_size_bytes: int = 0
    table_sizes: Dict[str, int] = field(default_factory=dict)
    index_sizes: Dict[str, int] = field(default_factory=dict)
    partitions: List[Dict[str, Any]] = field(default_factory=list)
    row_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "database_size_bytes": self.database_size_bytes,
            "table_sizes": self.table_sizes,
            "index_sizes": self.index_sizes,
            "partitions": self.partitions,
            "row_counts": self.row_counts,
        }
