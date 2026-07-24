"""
AKAAL Platform 7 — Enterprise Operational Reliability Domain Enums.
"""

from enum import Enum


class ServiceTier(str, Enum):
    TIER_0 = "TIER_0"  # Mission Critical Core (Zero Downtime)
    TIER_1 = "TIER_1"  # High Priority Business Service
    TIER_2 = "TIER_2"  # Standard Operational Service
    TIER_3 = "TIER_3"  # Batch / Non-Realtime Service


class CriticalityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    CRITICAL = "CRITICAL"


class IncidentSeverity(str, Enum):
    SEV_0 = "SEV_0"  # Complete Outage / Critical Impact
    SEV_1 = "SEV_1"  # Major Service Degradation
    SEV_2 = "SEV_2"  # Moderate Operational Impact
    SEV_3 = "SEV_3"  # Minor / Low Impact Issue


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    IDENTIFIED = "IDENTIFIED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class MaintenanceType(str, Enum):
    PLANNED_DOWNTIME = "PLANNED_DOWNTIME"
    CHANGE_WINDOW = "CHANGE_WINDOW"
    ROLLING_RESTART = "ROLLING_RESTART"
    HOTFIX_DEPLOYMENT = "HOTFIX_DEPLOYMENT"


class MaintenanceState(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RiskSeverity(str, Enum):
    EXTREME = "EXTREME"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
