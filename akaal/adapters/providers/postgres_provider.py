"""
Akaal — PostgreSQL Discovery Provider
=====================================
Discovery provider dedicated to PostgreSQL metadata discovery via PostgresAdapter.
"""

from typing import Any, Dict
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider


class PostgresDiscoveryProvider(GenericDiscoveryProvider):
    """PostgreSQL-specific discovery provider."""

    async def detect_engine(self) -> Dict[str, Any]:
        return {
            "system_type": "POSTGRESQL",
            "vendor": "PostgreSQL Global Development Group",
            "engine_name": "PostgreSQL",
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "PostgreSQL 15.2 on x86_64-pc-linux-gnu",
            "major": 15,
            "minor": 2,
            "patch": 0,
            "edition": "Community Enterprise",
            "build_number": "15.2-1",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        res = await super().detect_capabilities()
        res.update({
            "supports_cdc": True,
            "supports_partitioning": True,
            "supports_json": True,
            "supports_materialized_views": True,
            "supports_sequences": True,
        })
        return res

    async def discover_schema(self) -> Dict[str, Any]:
        if not self.adapter or not getattr(self.adapter, "is_connected", False) or not getattr(self.adapter, "_conn", None):
            return {"schemas": [], "tables": [], "foreign_keys": [], "views": []}

        if getattr(self.adapter, "mock_mode", False):
            return await super().discover_schema()

        import asyncio

        def _fetch_pg_metadata():
            with self.adapter._conn.cursor() as cur:
                # 1. Discover non-system schemas
                cur.execute("""
                    SELECT DISTINCT nspname 
                    FROM pg_namespace 
                    WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                      AND nspname NOT LIKE 'pg_%'
                    ORDER BY nspname
                """)
                schemas = [r[0] for r in cur.fetchall()]
                if not schemas:
                    schemas = ["public"]

                # 2. Discover tables per schema
                cur.execute("""
                    SELECT t.table_schema, t.table_name,
                           COALESCE(c.reltuples, 0)::bigint AS row_count,
                           COALESCE(pg_total_relation_size(quote_ident(t.table_schema) || '.' || quote_ident(t.table_name)), 0) AS size_bytes
                    FROM information_schema.tables t
                    LEFT JOIN pg_class c ON c.relname = t.table_name
                    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
                    WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND t.table_schema NOT LIKE 'pg_%'
                      AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_schema, t.table_name
                """)
                t_rows = cur.fetchall()
                tables = []
                for t_sch, t_name, r_count, s_bytes in t_rows:
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (t_sch, t_name))
                    cols = []
                    for col_name, col_type, is_null, col_def in cur.fetchall():
                        cols.append({
                            "name": col_name,
                            "type": col_type.upper(),
                            "nullable": is_null == "YES",
                            "default": col_def,
                        })

                    tables.append({
                        "table_name": t_name,
                        "schema_name": t_sch,
                        "row_count": max(0, int(r_count)),
                        "size_bytes": max(0, int(s_bytes)),
                        "columns": cols,
                        "indexes": [],
                        "constraints": [],
                    })

                # 3. Discover views
                cur.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.views
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_schema NOT LIKE 'pg_%'
                    ORDER BY table_schema, table_name
                """)
                views = []
                for v_sch, v_name in cur.fetchall():
                    views.append({"name": v_name, "schema_name": v_sch})

                return {
                    "schemas": schemas,
                    "tables": tables,
                    "foreign_keys": [],
                    "views": views,
                }

        return await asyncio.to_thread(_fetch_pg_metadata)
