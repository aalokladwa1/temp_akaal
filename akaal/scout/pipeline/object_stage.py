"""
Akaal — Object Discovery Stage
==============================
Stage 7: Discover procedures, functions, triggers, sequences with Policy control.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.object_inventory import ObjectInventory
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class ObjectDiscoveryStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "ObjectDiscovery"

    @property
    def dependencies(self) -> list:
        return ["SchemaDiscovery"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider and ctx.policy.collect_object_inventory:
            obj_data = await ctx.provider.discover_objects()
            ctx.object_inventory = ObjectInventory(
                procedures=obj_data.get("procedures", []),
                functions=obj_data.get("functions", []),
                triggers=obj_data.get("triggers", []),
                sequences=obj_data.get("sequences", []),
                custom_types=obj_data.get("custom_types", []),
            )
            if ctx.metrics:
                num_objs = (
                    len(ctx.object_inventory.procedures)
                    + len(ctx.object_inventory.functions)
                    + len(ctx.object_inventory.triggers)
                    + len(ctx.object_inventory.sequences)
                    + len(ctx.object_inventory.custom_types)
                )
                ctx.metrics.objects_discovered += num_objs

        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
