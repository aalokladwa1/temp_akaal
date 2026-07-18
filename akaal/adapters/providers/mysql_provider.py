"""
Akaal — MySQL Discovery Provider
================================
Discovery provider dedicated to MySQL metadata discovery via MySQLAdapter.
"""

from typing import Any, Dict
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider


class MySQLDiscoveryProvider(GenericDiscoveryProvider):
    """MySQL-specific discovery provider."""

    async def detect_engine(self) -> Dict[str, Any]:
        return {
            "system_type": "MYSQL",
            "vendor": "Oracle Corporation",
            "engine_name": "MySQL",
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "8.0.32 MySQL Community Server - GPL",
            "major": 8,
            "minor": 0,
            "patch": 32,
            "edition": "Community Enterprise",
            "build_number": "8.0.32",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        res = await super().detect_capabilities()
        res.update({
            "supports_cdc": True,
            "supports_partitioning": True,
            "supports_json": True,
            "supports_generated_columns": True,
        })
        return res
