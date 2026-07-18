"""
Akaal — Capability Detection Stage
==================================
Stage 3: Detect engine capability flags and feature support.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.capability_inventory import CapabilityInventory
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class CapabilityDetectionStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "CapabilityDetection"

    @property
    def dependencies(self) -> list:
        return ["VersionDetection"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            cap_data = await ctx.provider.detect_capabilities()
            ctx.capability_inventory = CapabilityInventory(
                supports_cdc=cap_data.get("supports_cdc", False),
                supports_partitioning=cap_data.get("supports_partitioning", False),
                supports_compression=cap_data.get("supports_compression", False),
                supports_encryption=cap_data.get("supports_encryption", False),
                supports_replication=cap_data.get("supports_replication", False),
                supports_json=cap_data.get("supports_json", False),
                supports_xml=cap_data.get("supports_xml", False),
                supports_spatial=cap_data.get("supports_spatial", False),
                supports_materialized_views=cap_data.get("supports_materialized_views", False),
                supports_stored_procedures=cap_data.get("supports_stored_procedures", False),
                supports_functions=cap_data.get("supports_functions", False),
                supports_triggers=cap_data.get("supports_triggers", False),
                supports_sequences=cap_data.get("supports_sequences", False),
                supports_generated_columns=cap_data.get("supports_generated_columns", False),
                supports_lob_streaming=cap_data.get("supports_lob_streaming", False),
                extra_capabilities=cap_data.get("extra_capabilities", {}),
            )
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
