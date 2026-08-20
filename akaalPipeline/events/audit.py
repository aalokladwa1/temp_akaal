"""akaalPipeline.events.audit
============================
Audit trail service for immutable actor/action correlation tracking.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    actor_id: str
    action: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    evidence_fingerprint: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditTrailService:
    def record_audit(
        self,
        actor_id: str,
        action: str,
        conn: sqlite3.Connection,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        evidence_fingerprint: Optional[str] = None,
    ) -> AuditRecord:
        audit_id = f"aud-{uuid.uuid4().hex}"

        now = datetime.now(timezone.utc).isoformat()
        rec = AuditRecord(
            audit_id=audit_id,
            actor_id=actor_id,
            action=action,
            correlation_id=correlation_id,
            causation_id=causation_id,
            evidence_fingerprint=evidence_fingerprint,
            created_at=now,
        )
        conn.execute(
            """
            INSERT INTO audit_trail (audit_id, actor_id, action, correlation_id, causation_id, evidence_fingerprint, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (rec.audit_id, rec.actor_id, rec.action, rec.correlation_id, rec.causation_id, rec.evidence_fingerprint, rec.created_at),
        )
        return rec
