"""
Akaal — Cluster Discovery Stage
===============================
Stage 5: Discover cluster topology and replication role.
"""

from datetime import datetime, timezone
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import ClusterInfo, StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage


class ClusterDiscoveryStage(BaseDiscoveryStage):

    @property
    def stage_name(self) -> str:
        return "ClusterDiscovery"

    @property
    def dependencies(self) -> list:
        return ["InstanceDiscovery"]

    async def execute(self, ctx: DiscoveryContext) -> StageDiagnostics:
        t0 = datetime.now(timezone.utc).isoformat()
        if ctx.provider:
            cl_data = await ctx.provider.discover_cluster()
            ctx.cluster_info = ClusterInfo(
                is_clustered=cl_data.get("is_clustered", False),
                role=cl_data.get("role", "PRIMARY"),
                node_count=cl_data.get("node_count", 1),
                nodes=cl_data.get("nodes", []),
                replication_lag_ms=cl_data.get("replication_lag_ms", 0),
            )
        t1 = datetime.now(timezone.utc).isoformat()
        return StageDiagnostics(
            stage_name=self.stage_name,
            status="SUCCESS",
            start_time=t0,
            end_time=t1,
            duration_ms=0.0,
        )
