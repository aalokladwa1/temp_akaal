"""
Akaal — Engine Detection Stage
==============================
Stage 1: Detect database engine details.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import EngineInfo, StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class EngineDetectionStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "EngineDetection"

    @property
    def dependencies(self) -> list:
        return []

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            eng_data = await ctx.provider.detect_engine()
            ctx.engine_info = EngineInfo(
                system_type=eng_data.get("system_type", "GENERIC"),
                vendor=eng_data.get("vendor", "Generic"),
                engine_name=eng_data.get("engine_name", "Generic Engine"),
            )
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
