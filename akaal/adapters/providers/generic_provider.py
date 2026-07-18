"""
Akaal — Generic Discovery Provider
===================================
Fallback discovery provider that leverages standard BaseAdapter capabilities.
"""

from typing import Any, Dict, List
from akaal.adapters.providers.base_provider import BaseDiscoveryProvider


class GenericDiscoveryProvider(BaseDiscoveryProvider):
    """Fallback provider for any database adapter implementing BaseAdapter."""

    async def check_read_only_permissions(self) -> bool:
        try:
            return await self.adapter.check_permissions()
        except Exception:
            return True

    async def detect_engine(self) -> Dict[str, Any]:
        system_type = getattr(self.adapter, "SYSTEM_TYPE", None)
        st_val = system_type.value if hasattr(system_type, "value") else str(system_type or "GENERIC")
        return {
            "system_type": st_val,
            "vendor": "Generic",
            "engine_name": st_val,
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "Generic 1.0",
            "major": 1,
            "minor": 0,
            "patch": 0,
            "edition": "Standard",
            "build_number": "1",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        caps = getattr(self.adapter, "CAPABILITIES", [])
        cap_names = [c.value if hasattr(c, "value") else str(c) for c in caps]
        return {
            "supports_cdc": "CDC_SUPPORT" in cap_names,
            "supports_partitioning": "PARTITION_MIGRATION" in cap_names,
            "supports_compression": True,
            "supports_encryption": True,
            "supports_replication": False,
            "supports_json": True,
            "supports_xml": True,
            "supports_spatial": False,
            "supports_materialized_views": True,
            "supports_stored_procedures": True,
            "supports_functions": True,
            "supports_triggers": True,
            "supports_sequences": True,
            "supports_generated_columns": True,
            "supports_lob_streaming": "LOB_STREAMING" in cap_names,
        }

    async def discover_instance(self) -> Dict[str, Any]:
        cfg = getattr(self.adapter, "config", None)
        return {
            "host": getattr(cfg, "host", "localhost"),
            "port": getattr(cfg, "port", 0),
            "database_name": getattr(cfg, "database_name", "default"),
            "server_version": "1.0",
            "max_connections": 100,
            "active_connections": 1,
            "uptime_seconds": 3600,
            "parameters": {},
        }

    async def discover_cluster(self) -> Dict[str, Any]:
        return {
            "is_clustered": False,
            "role": "PRIMARY",
            "node_count": 1,
            "nodes": [],
            "replication_lag_ms": 0,
        }

    async def discover_schema(self) -> Dict[str, Any]:
        tables: List[Dict[str, Any]] = []
        table_names = await self.adapter.discover_tables()
        for t_name in table_names:
            cols = await self.adapter.discover_columns(t_name)
            idxs = await self.adapter.discover_indexes(t_name)
            cons = await self.adapter.discover_constraints(t_name)
            tables.append({
                "table_name": t_name,
                "columns": cols,
                "indexes": idxs,
                "constraints": cons,
            })
        fks = await self.adapter.discover_foreign_keys()
        views = await self.adapter.discover_views()
        return {
            "schemas": ["public"],
            "tables": tables,
            "foreign_keys": fks,
            "views": views,
        }

    async def discover_objects(self) -> Dict[str, Any]:
        return {
            "procedures": [],
            "functions": [],
            "triggers": [],
            "sequences": [],
            "custom_types": [],
        }

    async def discover_storage(self) -> Dict[str, Any]:
        table_names = await self.adapter.discover_tables()
        table_sizes: Dict[str, int] = {}
        row_counts: Dict[str, int] = {}
        for t_name in table_names:
            try:
                row_counts[t_name] = await self.adapter.get_row_count(t_name)
            except Exception:
                row_counts[t_name] = 0
            table_sizes[t_name] = row_counts[t_name] * 128  # estimate

        return {
            "database_size_bytes": sum(table_sizes.values()),
            "table_sizes": table_sizes,
            "index_sizes": {},
            "partitions": [],
            "row_counts": row_counts,
        }
