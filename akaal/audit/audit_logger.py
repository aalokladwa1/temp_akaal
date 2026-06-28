"""
NexusForge — Immutable Audit Logger
=====================================
Provides enterprise-grade, immutable, structured audit logging.

Every workflow action, state transition, approval, incident, retry,
failover, and recovery MUST produce an audit entry.

TRD Section 13 Logging Requirements: Manager shall log every
  task assignment, workflow transition, checkpoint, approval,
  incident, retry, failover, recovery.

brain.md Section 14: No blind actions allowed.
  Metrics → Analysis → Decision → Action → Validation → Logging

Audit entries are:
  - Written to a structured JSON log file
  - Timestamped in UTC
  - Assigned sequential entry IDs
  - Never deleted or modified (append-only)
  - Checksummed for tamper detection
"""

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexusforge.audit")


# ---------------------------------------------------------------------------
# Audit Event Types
# ---------------------------------------------------------------------------

class AuditEventType:
    # Project lifecycle
    PROJECT_CREATED          = "PROJECT_CREATED"
    PROJECT_STATE_CHANGED    = "PROJECT_STATE_CHANGED"
    PROJECT_CANCELLED        = "PROJECT_CANCELLED"
    PROJECT_COMPLETED        = "PROJECT_COMPLETED"

    # Workflow
    WORKFLOW_STARTED         = "WORKFLOW_STARTED"
    WORKFLOW_PAUSED          = "WORKFLOW_PAUSED"
    WORKFLOW_RESUMED         = "WORKFLOW_RESUMED"
    WORKFLOW_STAGE_COMPLETE  = "WORKFLOW_STAGE_COMPLETE"

    # Task management
    TASK_ASSIGNED            = "TASK_ASSIGNED"
    TASK_STARTED             = "TASK_STARTED"
    TASK_COMPLETED           = "TASK_COMPLETED"
    TASK_FAILED              = "TASK_FAILED"
    TASK_CANCELLED           = "TASK_CANCELLED"
    TASK_RETRIED             = "TASK_RETRIED"

    # Discovery
    DISCOVERY_STARTED        = "DISCOVERY_STARTED"
    DISCOVERY_COMPLETED      = "DISCOVERY_COMPLETED"
    DISCOVERY_FAILED         = "DISCOVERY_FAILED"

    # Validation
    VALIDATION_STARTED       = "VALIDATION_STARTED"
    VALIDATION_PASSED        = "VALIDATION_PASSED"
    VALIDATION_FAILED        = "VALIDATION_FAILED"

    # GB
    GB_IMPORT_STARTED        = "GB_IMPORT_STARTED"
    GB_IMPORT_COMPLETED      = "GB_IMPORT_COMPLETED"
    GB_VALIDATION_PASSED     = "GB_VALIDATION_PASSED"
    GB_VALIDATION_FAILED     = "GB_VALIDATION_FAILED"

    # Human approval
    APPROVAL_REQUESTED       = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED         = "APPROVAL_GRANTED"
    APPROVAL_REJECTED        = "APPROVAL_REJECTED"
    APPROVAL_PAUSED          = "APPROVAL_PAUSED"

    # Migration
    MIGRATION_STARTED        = "MIGRATION_STARTED"
    MIGRATION_BATCH_COMPLETE = "MIGRATION_BATCH_COMPLETE"
    MIGRATION_BATCH_FAILED   = "MIGRATION_BATCH_FAILED"
    MIGRATION_COMPLETED      = "MIGRATION_COMPLETED"

    # CDC
    CDC_STARTED              = "CDC_STARTED"
    CDC_EVENT_PROCESSED      = "CDC_EVENT_PROCESSED"
    CDC_COMPLETED            = "CDC_COMPLETED"

    # Checkpoints
    CHECKPOINT_CREATED       = "CHECKPOINT_CREATED"
    CHECKPOINT_RESTORED      = "CHECKPOINT_RESTORED"
    CHECKPOINT_INVALIDATED   = "CHECKPOINT_INVALIDATED"

    # Incidents & Recovery
    INCIDENT_CREATED         = "INCIDENT_CREATED"
    INCIDENT_RESOLVED        = "INCIDENT_RESOLVED"
    RECOVERY_STARTED         = "RECOVERY_STARTED"
    RECOVERY_COMPLETED       = "RECOVERY_COMPLETED"

    # Failover
    FAILOVER_TRIGGERED       = "FAILOVER_TRIGGERED"
    FAILOVER_COMPLETED       = "FAILOVER_COMPLETED"

    # Loop Governor
    LOOP_WARNING             = "LOOP_WARNING"
    LOOP_STOP                = "LOOP_STOP"
    LOOP_ESCALATE            = "LOOP_ESCALATE"
    LOOP_FREEZE              = "LOOP_FREEZE"

    # System
    SYSTEM_STARTED           = "SYSTEM_STARTED"
    SYSTEM_FROZEN            = "SYSTEM_FROZEN"
    SYSTEM_UNFROZEN          = "SYSTEM_UNFROZEN"
    AGENT_REGISTERED         = "AGENT_REGISTERED"
    AGENT_STATUS_CHANGED     = "AGENT_STATUS_CHANGED"

    # Input Gateway
    GATEWAY_UPLOAD_RECEIVED      = "GATEWAY_UPLOAD_RECEIVED"
    GATEWAY_VALIDATION_PASSED    = "GATEWAY_VALIDATION_PASSED"
    GATEWAY_VALIDATION_FAILED    = "GATEWAY_VALIDATION_FAILED"
    GATEWAY_DB_DETECTED          = "GATEWAY_DB_DETECTED"
    GATEWAY_FORWARDED_TO_MANAGER = "GATEWAY_FORWARDED_TO_MANAGER"
    GATEWAY_REJECTED             = "GATEWAY_REJECTED"


# ---------------------------------------------------------------------------
# Audit Entry
# ---------------------------------------------------------------------------

class AuditEntry:
    """A single, immutable audit record."""

    def __init__(
        self,
        event_type: str,
        actor: str,                         # AgentType.value or username
        project_id: Optional[str],
        migration_id: Optional[str],
        description: str,
        details: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        import uuid
        self.entry_id = entry_id or str(uuid.uuid4())
        self.event_type = event_type
        self.actor = actor
        self.project_id = project_id
        self.migration_id = migration_id
        self.description = description
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        data = {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "description": self.description,
            "details": self.details,
            "timestamp": self.timestamp,
        }
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "description": self.description,
            "details": self.details,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
        }


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    Immutable, append-only audit log writer.

    Writes structured JSON entries to:
      1. A rotating JSONL log file (one entry per line)
      2. In-memory buffer (for querying during a session)

    Thread-safe: uses a threading lock for file writes.
    """

    def __init__(self, log_dir: str = "audit", log_filename: str = "audit.jsonl") -> None:
        self._log_path = Path(log_dir) / log_filename
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._sequence: int = 0

        # Set up Python logger for console output
        self._console_log = logging.getLogger("nexusforge.audit.console")

        logger.info("[AuditLogger] Initialized. Log file: %s", self._log_path)

    def log(
        self,
        event_type: str,
        actor: str,
        description: str,
        project_id: Optional[str] = None,
        migration_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Write an immutable audit entry.

        This is the ONLY method for creating audit records.
        All agents must call this for every significant action.
        """
        with self._lock:
            self._sequence += 1
            entry = AuditEntry(
                event_type=event_type,
                actor=actor,
                project_id=project_id,
                migration_id=migration_id,
                description=description,
                details={**(details or {}), "_seq": self._sequence},
            )
            self._entries.append(entry)
            self._write_to_file(entry)

        # Log to console at appropriate level
        log_level = self._get_log_level(event_type)
        self._console_log.log(
            log_level,
            "[AUDIT] %s | %s | project=%s | %s",
            event_type, actor, project_id, description
        )

        return entry

    def _write_to_file(self, entry: AuditEntry) -> None:
        """Append entry as a JSON line to the audit file."""
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.error("[AuditLogger] Failed to write audit entry: %s", exc)

    def _get_log_level(self, event_type: str) -> int:
        """Map event types to logging levels."""
        critical_events = {
            AuditEventType.LOOP_FREEZE,
            AuditEventType.SYSTEM_FROZEN,
            AuditEventType.INCIDENT_CREATED,
        }
        warning_events = {
            AuditEventType.TASK_FAILED,
            AuditEventType.VALIDATION_FAILED,
            AuditEventType.LOOP_WARNING,
            AuditEventType.LOOP_STOP,
            AuditEventType.LOOP_ESCALATE,
            AuditEventType.APPROVAL_REJECTED,
            AuditEventType.FAILOVER_TRIGGERED,
        }
        if event_type in critical_events:
            return logging.CRITICAL
        if event_type in warning_events:
            return logging.WARNING
        return logging.INFO

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_all(self) -> List[AuditEntry]:
        """Return all in-memory audit entries (current session)."""
        return list(self._entries)

    def get_by_project(self, project_id: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.project_id == project_id]

    def get_by_event_type(self, event_type: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.event_type == event_type]

    def get_approvals(self, project_id: str) -> List[AuditEntry]:
        approval_types = {
            AuditEventType.APPROVAL_REQUESTED,
            AuditEventType.APPROVAL_GRANTED,
            AuditEventType.APPROVAL_REJECTED,
        }
        return [
            e for e in self._entries
            if e.project_id == project_id and e.event_type in approval_types
        ]

    def verify_entry_integrity(self, entry: AuditEntry) -> bool:
        """Verify an audit entry has not been tampered with."""
        expected = entry._compute_checksum()
        return expected == entry.checksum

    def count(self) -> int:
        return len(self._entries)

    def summary(self) -> Dict[str, Any]:
        event_counts: Dict[str, int] = {}
        for e in self._entries:
            event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1
        return {
            "total_entries": len(self._entries),
            "log_file": str(self._log_path),
            "event_counts": event_counts,
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(log_dir: str = "audit") -> AuditLogger:
    """Return the global singleton AuditLogger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(log_dir=log_dir)
    return _audit_logger


def reset_audit_logger() -> None:
    """Reset singleton (tests only)."""
    global _audit_logger
    _audit_logger = None
