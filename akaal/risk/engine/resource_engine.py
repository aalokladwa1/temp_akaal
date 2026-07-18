"""
Akaal — Resource Estimation Engine
===================================
Single-responsibility engine computing Min, Recommended, Peak, and Burst resource requirements.
"""

from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.resource_estimate import ResourceLevelEstimate, ResourceEstimate


class ResourceEngine:
    """Estimates infrastructure resources required for execution."""

    def estimate_resources(self, ctx: RiskContext) -> ResourceEstimate:
        c_model = ctx.canonical_model
        nodes = c_model.canonical_graph.get("nodes", [])

        table_count = max(1, sum(1 for o in nodes if o.get("object_type") == "CanonicalTable"))

        cpu_rec = max(2.0, min(16.0, table_count * 0.5))
        mem_rec = max(4.0, min(64.0, table_count * 1.0))

        return ResourceEstimate(
            cpu_cores=ResourceLevelEstimate(minimum=1.0, recommended=cpu_rec, peak=cpu_rec * 2, burst=cpu_rec * 4),
            memory_gb=ResourceLevelEstimate(minimum=2.0, recommended=mem_rec, peak=mem_rec * 2, burst=mem_rec * 4),
            disk_gb=ResourceLevelEstimate(minimum=10.0, recommended=50.0, peak=100.0, burst=200.0),
            network_mbps=ResourceLevelEstimate(minimum=100.0, recommended=500.0, peak=1000.0, burst=2000.0),
            workers=ResourceLevelEstimate(minimum=1.0, recommended=max(2.0, cpu_rec), peak=max(4.0, cpu_rec * 2), burst=max(8.0, cpu_rec * 4)),
            temp_storage_gb=20.0,
        )
