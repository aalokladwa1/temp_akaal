"""
akaalEngine.fabric.regional_operation.models
================================================
P7B.26 -- Multi-Region Operation data model.

Deliberately thin: a region is identified purely by `ExecutionSite.region` (the existing
P7B.5 field -- no new region identity is invented here), and region OPERATIONAL health is
always a computed rollup of P7B.24 SiteCoordinator's per-site CoordinationView, never an
independently-tracked parallel state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class RegionOperationalState(str, Enum):
    HEALTHY = "HEALTHY"          # at least one site with CoordinationView.AVAILABLE
    DEGRADED = "DEGRADED"        # no AVAILABLE site, but at least one DEGRADED site
    UNAVAILABLE = "UNAVAILABLE"  # zero AVAILABLE/DEGRADED sites among all registered sites
    UNKNOWN = "UNKNOWN"          # no sites at all are registered under this region label


@dataclass(frozen=True)
class RegionHealthSnapshot:
    region: str
    site_ids: Tuple[str, ...] = field(default_factory=tuple)
    available_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    degraded_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    unavailable_site_ids: Tuple[str, ...] = field(default_factory=tuple)
    state: RegionOperationalState = RegionOperationalState.UNKNOWN
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    def is_operationally_usable(self) -> bool:
        return self.state in (RegionOperationalState.HEALTHY, RegionOperationalState.DEGRADED)
