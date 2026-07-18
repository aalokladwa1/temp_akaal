"""
Akaal — Storage Discovery Stage
===============================
Stage 8: Discover storage statistics with Policy control.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.storage_inventory import StorageInventory
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class StorageDiscoveryStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "StorageDiscovery"

    @property
    def dependencies(self) -> list:
        return ["CapabilityDetection"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider and ctx.policy.collect_storage_statistics:
            stg_data = await ctx.provider.discover_storage()
            ctx.storage_inventory = StorageInventory(
                database_size_bytes=stg_data.get("database_size_bytes", 0),
                table_sizes=stg_data.get("table_sizes", {}),
                index_sizes=stg_data.get("index_sizes", {}),
                partitions=stg_data.get("partitions", []),
                row_counts=stg_data.get("row_counts", {}),
            )
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
