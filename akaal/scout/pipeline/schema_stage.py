"""
Akaal — Schema Discovery Stage
==============================
Stage 6: Discover schema inventory with DiscoveryPolicy filtering.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.schema_inventory import SchemaInventory, TableMetadata
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class SchemaDiscoveryStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "SchemaDiscovery"

    @property
    def dependencies(self) -> list:
        return ["CapabilityDetection"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            sch_data = await ctx.provider.discover_schema()
            
            # Filter schemas based on policy
            raw_schemas = sch_data.get("schemas", ["public"])
            allowed_schemas = [s for s in raw_schemas if ctx.policy.is_schema_allowed(s)]
            if not allowed_schemas:
                allowed_schemas = ["public"]

            table_objs = []
            for t_info in sch_data.get("tables", []):
                t_name = t_info.get("table_name", "unknown")
                s_name = t_info.get("schema_name", "public")
                
                if not ctx.policy.is_schema_allowed(s_name) or not ctx.policy.is_table_allowed(t_name):
                    if ctx.metrics:
                        ctx.metrics.record_skipped_object()
                    continue

                cols = t_info.get("columns", [])
                idxs = t_info.get("indexes", [])
                cons = t_info.get("constraints", [])
                table_objs.append(TableMetadata(
                    table_name=t_name,
                    schema_name=s_name,
                    columns=cols,
                    indexes=idxs,
                    constraints=cons,
                ))

            ctx.schema_inventory = SchemaInventory(
                schemas=allowed_schemas,
                tables=table_objs,
                foreign_keys=sch_data.get("foreign_keys", []),
                views=sch_data.get("views", []),
            )

            if ctx.metrics:
                ctx.metrics.schemas_discovered = len(ctx.schema_inventory.schemas)
                total_objs = len(table_objs) + len(sch_data.get("views", []))
                ctx.metrics.objects_discovered += total_objs

        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
