"""
Akaal — Instance Discovery Stage
================================
Stage 4: Discover instance configuration, connection limits, and server params.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import InstanceInfo, StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class InstanceDiscoveryStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "InstanceDiscovery"

    @property
    def dependencies(self) -> list:
        return ["EngineDetection"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            inst_data = await ctx.provider.discover_instance()
            ctx.instance_info = InstanceInfo(
                host=inst_data.get("host", ctx.request.connection_config.host),
                port=inst_data.get("port", ctx.request.connection_config.port),
                database_name=inst_data.get("database_name", ctx.request.connection_config.database_name),
                server_version=inst_data.get("server_version", "1.0"),
                max_connections=inst_data.get("max_connections", 100),
                active_connections=inst_data.get("active_connections", 1),
                uptime_seconds=inst_data.get("uptime_seconds", 3600),
                parameters=inst_data.get("parameters", {}),
            )
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
