"""
AKAAL Enterprise Platform — Metadata Catalog
=============================================
Centralized, reusable repository for schemas, tables, columns, indexes, constraints, lineage, statistics, and risk ratings.
"""

from typing import Any, Dict, List, Optional
from akaal.core.interfaces.enterprise_interfaces import IMetadataCatalog


class CentralMetadataCatalog(IMetadataCatalog):
    """Reusable Enterprise Metadata Catalog."""

    def __init__(self) -> None:
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def store_schema_metadata(self, schema_name: str, metadata: Dict[str, Any]) -> None:
        self._schemas[schema_name] = metadata

    def get_schema_metadata(self, schema_name: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(schema_name)

    def get_table_metadata(self, schema_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        schema = self._schemas.get(schema_name)
        if schema and "tables" in schema:
            for tbl in schema["tables"]:
                if tbl.get("name") == table_name:
                    return tbl
        return None

    def list_tables(self, schema_name: str) -> List[str]:
        schema = self._schemas.get(schema_name)
        if schema and "tables" in schema:
            return [t.get("name") for t in schema["tables"] if "name" in t]
        return []
