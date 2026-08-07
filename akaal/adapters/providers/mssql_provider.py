"""
Akaal — Microsoft SQL Server Discovery Provider
==============================================
Discovery provider dedicated to MSSQL metadata discovery via MSSQLAdapter.
"""

from typing import Any, Dict
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider


class MSSQLDiscoveryProvider(GenericDiscoveryProvider):
    """Microsoft SQL Server-specific discovery provider."""

    async def detect_engine(self) -> Dict[str, Any]:
        return {
            "system_type": "SQLSERVER",
            "vendor": "Microsoft Corporation",
            "engine_name": "Microsoft SQL Server",
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "Microsoft SQL Server 2019 (RTM) - 15.0.2000.5",
            "major": 15,
            "minor": 0,
            "patch": 2000,
            "edition": "Standard Edition",
            "build_number": "15.0.2000.5",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        res = await super().detect_capabilities()
        res.update({
            "supports_cdc": True,
            "supports_partitioning": True,
            "supports_json": True,
            "supports_sequences": True,
        })
        return res
