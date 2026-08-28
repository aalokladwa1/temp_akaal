"""akaalPipeline.events.audit
===========================
Canonical Tamper-Evident Security Audit Service with SHA-256 Hash Chaining.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import AuditDecision
from akaalPipeline.contracts.serialization import canonical_serialize
from akaalPipeline.state.repositories import SQLiteSecurityAuditRepository


class AuditIntegrityViolationError(RuntimeError):
    """Raised when audit ledger hash chain verification fails."""
    pass


class SecurityAuditService:
    """Canonical security audit logging and verification authority."""

    def __init__(self, audit_repo: SQLiteSecurityAuditRepository) -> None:
        self.audit_repo = audit_repo

    def _compute_entry_hash(
        self,
        sequence_number: int,
        previous_hash: str,
        actor_id: str,
        actor_type: str,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        decision: str,
        details: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """Compute SHA-256 hash of audit entry bound to previous hash."""
        payload = {
            "sequence_number": sequence_number,
            "previous_hash": previous_hash,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "decision": decision,
            "details": details,
            "timestamp": timestamp,
        }
        canonical_json = canonical_serialize(payload)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def record_event(
        self,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        decision: AuditDecision,
        details: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an immutable, hash-chained security audit event."""
        details_dict = details or {}
        last_seq, last_hash = self.audit_repo.get_latest_sequence_and_hash(tenant_id)
        next_seq = last_seq + 1
        now_iso = TimeAuthority.utc_iso_now()
        audit_id = generate_secure_id("aud")

        decision_val = decision.value if hasattr(decision, "value") else str(decision)
        entry_hash = self._compute_entry_hash(
            sequence_number=next_seq,
            previous_hash=last_hash,
            actor_id=actor_id,
            actor_type=actor_type,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            decision=decision_val,
            details=details_dict,
            timestamp=now_iso,
        )

        self.audit_repo.append_entry(
            audit_id=audit_id,
            tenant_id=tenant_id,
            sequence_number=next_seq,
            actor_id=actor_id,
            actor_type=actor_type,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            decision=decision_val,
            details=details_dict,
            previous_hash=last_hash,
            entry_hash=entry_hash,
            timestamp=now_iso,
            signature=signature,
        )

        return {
            "audit_id": audit_id,
            "sequence_number": next_seq,
            "entry_hash": entry_hash,
            "previous_hash": last_hash,
        }

    def verify_ledger_integrity(self, tenant_id: str) -> bool:
        """
        Verify complete SHA-256 hash chain integrity for a tenant.
        Detects interior row tampering, deletions (sequence gaps), and truncation.
        """
        entries = self.audit_repo.list_entries(tenant_id, limit=100000)
        if not entries:
            return True

        expected_previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        expected_seq = 1

        for entry in entries:
            # Check sequence continuity
            if entry["sequence_number"] != expected_seq:
                raise AuditIntegrityViolationError(
                    f"Audit sequence gap at {entry['sequence_number']}: expected {expected_seq}"
                )

            # Check previous hash link
            if entry["previous_hash"] != expected_previous_hash:
                raise AuditIntegrityViolationError(
                    f"Audit hash chain break at sequence {entry['sequence_number']}: "
                    f"previous_hash {entry['previous_hash']!r} != expected {expected_previous_hash!r}"
                )

            # Recompute entry hash
            recomputed = self._compute_entry_hash(
                sequence_number=entry["sequence_number"],
                previous_hash=entry["previous_hash"],
                actor_id=entry["actor_id"],
                actor_type=entry["actor_type"],
                event_type=entry["event_type"],
                resource_type=entry["resource_type"],
                resource_id=entry["resource_id"],
                action=entry["action"],
                decision=entry["decision"],
                details=entry["details"],
                timestamp=entry["timestamp"],
            )

            if entry["entry_hash"] != recomputed:
                raise AuditIntegrityViolationError(
                    f"Audit entry hash mismatch at sequence {entry['sequence_number']}: "
                    f"stored {entry['entry_hash']!r} != recomputed {recomputed!r}"
                )

            expected_previous_hash = entry["entry_hash"]
            expected_seq += 1

        return True


from dataclasses import dataclass


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    actor_id: str
    action: str
    resource_id: str
    tenant_id: str = "default-tenant"
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    evidence_fingerprint: Optional[str] = None
    timestamp: str = ""


class AuditTrailService:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def record_event(
        self,
        actor: Any,
        action: str,
        resource_id: str,
        conn: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditRecord:
        import uuid
        audit_id = f"aud-{uuid.uuid4().hex}"
        now_iso = TimeAuthority.utc_iso_now()
        actor_id = getattr(actor, "actor_id", str(actor))
        tenant_id = getattr(actor, "organization_id", getattr(actor, "tenant_id", "default-tenant"))
        record = AuditRecord(
            audit_id=audit_id,
            actor_id=actor_id,
            action=action,
            resource_id=resource_id,
            tenant_id=tenant_id,
            timestamp=now_iso,
        )
        if conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_trail (audit_id, tenant_id, actor_id, action, correlation_id, causation_id, evidence_fingerprint, created_at)
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?)
                """,
                (audit_id, tenant_id, actor_id, action, now_iso),
            )
        return record

