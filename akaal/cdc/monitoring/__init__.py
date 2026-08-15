"""
AKAAL CDC Monitoring & Operational Telemetry Package (P3.9).
============================================================
Provides safe-by-default, backend-authoritative read models aggregating P3.1–P3.8 runtime telemetry.
"""

from akaal.cdc.monitoring.domain import CDCMonitoringSnapshot
from akaal.cdc.monitoring.aggregator import CDCMonitoringAggregator

__all__ = [
    "CDCMonitoringSnapshot",
    "CDCMonitoringAggregator",
]
