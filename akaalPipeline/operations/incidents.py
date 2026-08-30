"""akaalPipeline.operations.incidents
==================================
P6.7 Incident Authority.
Manages operational incidents as response/correlation containers above alerts.
Maintains a durable, reconstructable timeline of operational actions and diagnostics.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.enums import IncidentSeverity, IncidentStatus, PipelineErrorCode
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.operations.incidents")


@dataclass(frozen=True)
class IncidentRecord:
    """Operational incident container."""
    incident_id: str
    tenant_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    summary: str
    migration_id: Optional[str] = None
    node_id: Optional[str] = None
    correlation_key: Optional[str] = None
    owner_actor_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "summary": self.summary,
            "migration_id": self.migration_id,
            "node_id": self.node_id,
            "correlation_key": self.correlation_key,
            "owner_actor_id": self.owner_actor_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }


@dataclass(frozen=True)
class IncidentTimelineRecord:
    """Durable timeline event for an incident."""
    event_id: str
    incident_id: str
    tenant_id: str
    event_type: str  # CREATED, ALERT_ATTACHED, SEVERITY_CHANGED, STATUS_CHANGED, DIAGNOSTIC_LINKED, ACTION_TAKEN
    actor_id: str
    details: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "incident_id": self.incident_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "details": self.details,
            "created_at": self.created_at,
        }


class IncidentService:
    """P6.7 Backend Incident Authority."""

    def create_incident(
        self,
        tenant_id: str,
        title: str,
        severity: IncidentSeverity,
        summary: str,
        conn: sqlite3.Connection,
        migration_id: Optional[str] = None,
        node_id: Optional[str] = None,
        correlation_key: Optional[str] = None,
        actor: Optional[PipelineActorContext] = None,
    ) -> IncidentRecord:
        """Creates an incident and logs its creation to the durable timeline."""
        incident_id = f"inc-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        actor_id = actor.actor_id if actor else "system"

        incident = IncidentRecord(
            incident_id=incident_id,
            tenant_id=tenant_id,
            title=title,
            severity=severity,
            status=IncidentStatus.OPEN,
            summary=summary,
            migration_id=migration_id,
            node_id=node_id,
            correlation_key=correlation_key,
            owner_actor_id=actor_id,
            created_at=now_iso,
            updated_at=now_iso,
        )
        conn.execute(
            """
            INSERT INTO incidents (
                incident_id, tenant_id, title, severity, status, summary,
                migration_id, node_id, correlation_key, owner_actor_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident.incident_id,
                incident.tenant_id,
                incident.title,
                incident.severity.value,
                incident.status.value,
                incident.summary,
                incident.migration_id,
                incident.node_id,
                incident.correlation_key,
                incident.owner_actor_id,
                incident.created_at,
                incident.updated_at,
            ),
        )

        self.record_timeline_event(
            incident_id=incident_id,
            tenant_id=tenant_id,
            event_type="CREATED",
            details={"title": title, "severity": severity.value, "summary": summary},
            actor_id=actor_id,
            conn=conn,
        )
        return incident

    def attach_alert(
        self,
        incident_id: str,
        alert_id: str,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
    ) -> None:
        """Attaches an alert to an incident."""
        incident = self.get_incident(incident_id, conn)
        if not incident:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Incident {incident_id!r} not found.")

        now_iso = datetime.now(timezone.utc).isoformat()
        actor_id = actor.actor_id if actor else "system"
        conn.execute(
            """
            INSERT OR IGNORE INTO incident_alert_links (incident_id, alert_id, attached_at)
            VALUES (?, ?, ?)
            """,
            (incident_id, alert_id, now_iso),
        )

        self.record_timeline_event(
            incident_id=incident_id,
            tenant_id=incident.tenant_id,
            event_type="ALERT_ATTACHED",
            details={"alert_id": alert_id},
            actor_id=actor_id,
            conn=conn,
        )

    def record_timeline_event(
        self,
        incident_id: str,
        tenant_id: str,
        event_type: str,
        details: Dict[str, Any],
        actor_id: str,
        conn: sqlite3.Connection,
    ) -> IncidentTimelineRecord:
        """Appends a durable timeline event to an incident."""
        event_id = f"evt-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        evt = IncidentTimelineRecord(
            event_id=event_id,
            incident_id=incident_id,
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            details=details,
            created_at=now_iso,
        )
        conn.execute(
            """
            INSERT INTO incident_timeline (event_id, incident_id, tenant_id, event_type, actor_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (evt.event_id, evt.incident_id, evt.tenant_id, evt.event_type, evt.actor_id, json.dumps(evt.details), evt.created_at),
        )
        return evt

    def update_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        reason: Optional[str] = None,
    ) -> IncidentRecord:
        """Transitions an incident status and records the change in the timeline."""
        incident = self.get_incident(incident_id, conn)
        if not incident:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Incident {incident_id!r} not found.")

        now_iso = datetime.now(timezone.utc).isoformat()
        actor_id = actor.actor_id if actor else "system"
        resolved_at = now_iso if status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED) else None

        conn.execute(
            """
            UPDATE incidents
            SET status = ?, resolved_at = ?, updated_at = ?
            WHERE incident_id = ?
            """,
            (status.value, resolved_at, now_iso, incident_id),
        )

        self.record_timeline_event(
            incident_id=incident_id,
            tenant_id=incident.tenant_id,
            event_type="STATUS_CHANGED",
            details={"from_status": incident.status.value, "to_status": status.value, "reason": reason or ""},
            actor_id=actor_id,
            conn=conn,
        )
        return self.get_incident(incident_id, conn)  # type: ignore

    def get_incident(self, incident_id: str, conn: sqlite3.Connection) -> Optional[IncidentRecord]:
        cur = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
        row = cur.fetchone()
        return self._row_to_incident(row) if row else None

    def list_incidents(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        status: Optional[IncidentStatus] = None,
        limit: int = 50,
    ) -> List[IncidentRecord]:
        """Lists incidents filtered by tenant and optional status."""
        if status:
            cur = conn.execute(
                """
                SELECT * FROM incidents
                WHERE tenant_id = ? AND status = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (tenant_id, status.value, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT * FROM incidents
                WHERE tenant_id = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (tenant_id, limit),
            )
        return [self._row_to_incident(r) for r in cur.fetchall()]

    def get_timeline(self, incident_id: str, conn: sqlite3.Connection) -> List[IncidentTimelineRecord]:
        cur = conn.execute(
            "SELECT * FROM incident_timeline WHERE incident_id = ? ORDER BY created_at ASC",
            (incident_id,),
        )
        results: List[IncidentTimelineRecord] = []
        for r in cur.fetchall():
            results.append(
                IncidentTimelineRecord(
                    event_id=r["event_id"],
                    incident_id=r["incident_id"],
                    tenant_id=r["tenant_id"],
                    event_type=r["event_type"],
                    actor_id=r["actor_id"],
                    details=json.loads(r["details"]) if r["details"] else {},
                    created_at=r["created_at"],
                )
            )
        return results

    def get_attached_alerts(self, incident_id: str, conn: sqlite3.Connection) -> List[str]:
        cur = conn.execute(
            "SELECT alert_id FROM incident_alert_links WHERE incident_id = ? ORDER BY attached_at ASC",
            (incident_id,),
        )
        return [r["alert_id"] for r in cur.fetchall()]

    def _row_to_incident(self, row: sqlite3.Row) -> IncidentRecord:
        return IncidentRecord(
            incident_id=row["incident_id"],
            tenant_id=row["tenant_id"],
            title=row["title"],
            severity=IncidentSeverity(row["severity"]),
            status=IncidentStatus(row["status"]),
            summary=row["summary"],
            migration_id=row["migration_id"],
            node_id=row["node_id"],
            correlation_key=row["correlation_key"],
            owner_actor_id=row["owner_actor_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_at=row["resolved_at"],
        )
