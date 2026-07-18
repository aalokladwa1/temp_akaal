"""
Akaal — Scout Platform API
==========================
Public API for source environment intelligence & metadata discovery.
"""

from typing import Optional, Union
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_request import DiscoveryRequest
from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.scout.orchestrator.discovery_orchestrator import DiscoveryOrchestrator


class ScoutPlatform:
    """
    Public entry point for the Scout Platform subsystem.
    Future modules (Rulebook, Decoder, Risk, Planner, Advisor) consume the DiscoveryReport returned here.
    """

    _orchestrator: Optional[DiscoveryOrchestrator] = None

    @classmethod
    def get_orchestrator(cls) -> DiscoveryOrchestrator:
        if cls._orchestrator is None:
            cls._orchestrator = DiscoveryOrchestrator()
        return cls._orchestrator

    @classmethod
    async def discover(
        cls,
        target: Union[DiscoveryRequest, ConnectionConfig],
        force_refresh: bool = False,
        ttl_seconds: Optional[int] = None,
    ) -> DiscoveryReport:
        """
        Discover and profile source database environment.
        Strictly READ-ONLY. Returns normalized DiscoveryReport.
        """
        if isinstance(target, ConnectionConfig):
            req = DiscoveryRequest(
                connection_config=target,
                force_refresh=force_refresh,
                ttl_seconds=ttl_seconds,
            )
        elif isinstance(target, DiscoveryRequest):
            req = target
        else:
            raise TypeError(f"Invalid target type for discover: {type(target)}")

        orchestrator = cls.get_orchestrator()
        return await orchestrator.execute_discovery(req)


async def discover(
    connection_config: ConnectionConfig,
    force_refresh: bool = False,
    ttl_seconds: Optional[int] = None,
) -> DiscoveryReport:
        """Convenience top-level async function for source discovery."""
        return await ScoutPlatform.discover(connection_config, force_refresh=force_refresh, ttl_seconds=ttl_seconds)
