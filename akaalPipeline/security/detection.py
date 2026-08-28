"""akaalPipeline.security.detection
==================================
Canonical Real-Time Security Threat Detector.
Analyzes authentication failures, IDOR attempts, replay attacks, seal tampering, and zombie workers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import SecurityAlertSeverity


@dataclass(frozen=True)
class SecurityAlertEvent:
    """Structured security threat alert."""

    alert_id: str
    tenant_id: str
    threat_type: str
    severity: SecurityAlertSeverity
    description: str
    actor_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "tenant_id": self.tenant_id,
            "threat_type": self.threat_type,
            "severity": self.severity.value,
            "description": self.description,
            "actor_id": self.actor_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class SecurityThreatDetector:
    """Canonical real-time security threat detection and alerting authority."""

    def __init__(
        self,
        alert_callback: Optional[Callable[[SecurityAlertEvent], None]] = None,
    ) -> None:
        self.alert_callback = alert_callback
        self.alerts: List[SecurityAlertEvent] = []

    def _emit_alert(
        self,
        tenant_id: str,
        threat_type: str,
        severity: SecurityAlertSeverity,
        description: str,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityAlertEvent:
        alert = SecurityAlertEvent(
            alert_id=generate_secure_id("alt"),
            tenant_id=tenant_id,
            threat_type=threat_type,
            severity=severity,
            description=description,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            timestamp=TimeAuthority.utc_iso_now(),
        )
        self.alerts.append(alert)
        if self.alert_callback:
            self.alert_callback(alert)
        return alert

    def record_auth_failure(self, tenant_id: str, username: str, client_ip: Optional[str], fail_count: int) -> Optional[SecurityAlertEvent]:
        """Detect and alert on brute force authentication attacks."""
        if fail_count >= 5:
            return self._emit_alert(
                tenant_id=tenant_id,
                threat_type="BRUTE_FORCE_AUTHENTICATION_ATTEMPT",
                severity=SecurityAlertSeverity.HIGH if fail_count < 10 else SecurityAlertSeverity.CRITICAL,
                description=f"Multiple consecutive failed logins ({fail_count}) for user {username!r}",
                actor_id=username,
                details={"failed_attempts": fail_count, "client_ip": client_ip},
            )
        return None

    def record_cross_tenant_access_attempt(self, actor_tenant: str, target_tenant: str, resource_id: str, actor_id: str) -> SecurityAlertEvent:
        """Detect and alert on cross-tenant IDOR attacks."""
        return self._emit_alert(
            tenant_id=actor_tenant,
            threat_type="CROSS_TENANT_IDOR_PROBING",
            severity=SecurityAlertSeverity.CRITICAL,
            description=f"Principal {actor_id!r} from tenant {actor_tenant!r} attempted access to foreign tenant {target_tenant!r}",
            actor_id=actor_id,
            resource_id=resource_id,
            details={"actor_tenant": actor_tenant, "target_tenant": target_tenant},
        )

    def record_replay_attempt(self, tenant_id: str, token_or_nonce: str, actor_id: Optional[str]) -> SecurityAlertEvent:
        """Detect and alert on token or nonce replay attacks."""
        return self._emit_alert(
            tenant_id=tenant_id,
            threat_type="TOKEN_OR_NONCE_REPLAY_ATTACK",
            severity=SecurityAlertSeverity.HIGH,
            description="Duplicate token or cryptographic nonce reuse detected",
            actor_id=actor_id,
            details={"nonce_or_token_prefix": token_or_nonce[:16] if token_or_nonce else ""},
        )

    def record_seal_tamper_attempt(self, tenant_id: str, migration_id: str, expected_seal: str, actual_seal: str) -> SecurityAlertEvent:
        """Detect and alert on execution seal mismatch."""
        return self._emit_alert(
            tenant_id=tenant_id,
            threat_type="EXECUTION_SEAL_INTEGRITY_VIOLATION",
            severity=SecurityAlertSeverity.CRITICAL,
            description=f"Execution seal fingerprint mismatch on migration {migration_id!r}",
            resource_type="MIGRATION",
            resource_id=migration_id,
            details={"expected_seal": expected_seal, "actual_seal": actual_seal},
        )

    def record_fencing_epoch_violation(self, tenant_id: str, migration_id: str, worker_epoch: int, current_epoch: int) -> SecurityAlertEvent:
        """Detect and alert on zombie worker or stale fencing token commits."""
        return self._emit_alert(
            tenant_id=tenant_id,
            threat_type="ZOMBIE_WORKER_STALE_FENCING_EPOCH",
            severity=SecurityAlertSeverity.CRITICAL,
            description=f"Stale worker attempted commit with epoch {worker_epoch} while current authoritative epoch is {current_epoch}",
            resource_type="MIGRATION",
            resource_id=migration_id,
            details={"worker_epoch": worker_epoch, "current_epoch": current_epoch},
        )

    def record_unauthorized_escalation(self, tenant_id: str, actor_id: str, target_role: str) -> SecurityAlertEvent:
        """Detect and alert on unauthorized privilege escalation attempts."""
        return self._emit_alert(
            tenant_id=tenant_id,
            threat_type="UNAUTHORIZED_PRIVILEGE_ESCALATION_ATTEMPT",
            severity=SecurityAlertSeverity.HIGH,
            description=f"Principal {actor_id!r} attempted unauthorized escalation to role {target_role!r}",
            actor_id=actor_id,
            details={"target_role": target_role},
        )
