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
