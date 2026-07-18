"""
Akaal — Discovery Audit Model
=============================
Audit trail for Scout platform discovery sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class DiscoveryAudit:
    """Audit record capturing discovery session metadata."""
    discovery_id: str
    request_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    authenticated_user: str = "system"
    target_endpoint: str = "localhost:5432"
    database_engine: str = "POSTGRESQL"
    discovery_profile: str = "STANDARD"
    discovery_policy_hash: str = ""
    report_hash: str = ""
    fingerprint: str = ""
    duration_ms: float = 0.0
    result: str = "SUCCESS"  # "SUCCESS", "PARTIAL", "FAILED"
    failure_reason: Optional[str] = None
    warning_count: int = 0
    provider_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "discovery_id": self.discovery_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "authenticated_user": self.authenticated_user,
            "target_endpoint": self.target_endpoint,
            "database_engine": self.database_engine,
            "discovery_profile": self.discovery_profile,
            "discovery_policy_hash": self.discovery_policy_hash,
            "report_hash": self.report_hash,
            "fingerprint": self.fingerprint,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "failure_reason": self.failure_reason,
            "warning_count": self.warning_count,
            "provider_version": self.provider_version,
        }
