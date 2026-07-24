"""HealthSnapshot, SLASnapshot, and ReliabilitySummary Dashboard Data Models."""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class HealthSnapshot:
    """Canonical health snapshot of system components and dependencies."""

    timestamp: float = field(default_factory=time.time)
    overall_health_score: float = 100.0
    active_incidents: int = 0
    component_scores: Dict[str, float] = field(default_factory=dict)
    unhealthy_dependencies: List[str] = field(default_factory=list)


@dataclass
class SLASnapshot:
    """SLA metrics snapshot (Availability, MTTR, MTBF)."""

    timestamp: float = field(default_factory=time.time)
    availability_pct: float = 99.99
    mttr_seconds: float = 4.2
    mtbf_hours: float = 720.0
    total_retries: int = 12
    successful_recoveries: int = 12
    circuit_breaker_trips: int = 0


@dataclass
class ReliabilitySummary:
    """Comprehensive summary data model for executive dashboards."""

    health: HealthSnapshot = field(default_factory=HealthSnapshot)
    sla: SLASnapshot = field(default_factory=SLASnapshot)
    active_profile: str = "ENTERPRISE"
    system_status: str = "OPERATIONAL"
