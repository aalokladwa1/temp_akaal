"""
Akaal — Version Detection Stage
===============================
Stage 2: Detect version, edition, build number.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class VersionDetectionStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "VersionDetection"

    @property
    def dependencies(self) -> list:
        return ["EngineDetection"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            ver_data = await ctx.provider.detect_version()
            ctx.version_info = ver_data
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
