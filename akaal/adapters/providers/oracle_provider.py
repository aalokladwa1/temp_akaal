"""
Akaal — Oracle Discovery Provider
=================================
Discovery provider dedicated to Oracle metadata discovery via OracleAdapter.
"""

from typing import Any, Dict
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider


class OracleDiscoveryProvider(GenericDiscoveryProvider):
    """Oracle-specific discovery provider."""

    async def detect_engine(self) -> Dict[str, Any]:
        return {
            "system_type": "ORACLE",
            "vendor": "Oracle Corporation",
            "engine_name": "Oracle Database",
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "Oracle Database 19c Enterprise Edition Release 19.0.0.0.0",
            "major": 19,
            "minor": 0,
            "patch": 0,
            "edition": "Enterprise Edition",
            "build_number": "19.3.0",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        res = await super().detect_capabilities()
        res.update({
            "supports_cdc": True,
            "supports_partitioning": True,
            "supports_lob_streaming": True,
            "supports_sequences": True,
            "supports_materialized_views": True,
        })
        return res
