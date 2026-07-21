"""
AKAAL Platform 5 — Structured Audit Logger

Provides thread-safe JSON audit logging for all schema state mutations and DDL operations.
"""

from dataclasses import asdict, dataclass
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from akaal.schema.observability.tracer import SchemaTracer


@dataclass
class AuditLogEntry:
    timestamp: float
    level: str
    event_name: str
    trace_id: str
    correlation_id: str
    tx_id: str
    details: Dict[str, Any]


class StructuredAuditLogger:
    """Thread-safe structured audit logger emitting JSON formatted events."""

    def __init__(self, logger_name: str = "akaal.schema.audit") -> None:
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        self._lock = threading.RLock()
        self._audit_records: List[AuditLogEntry] = []

    def log_event(self, event_name: str, level: str = "INFO", details: Optional[Dict[str, Any]] = None) -> AuditLogEntry:
        ctx = SchemaTracer.get_current_context()
        entry = AuditLogEntry(
            timestamp=time.time(),
            level=level.upper(),
            event_name=event_name,
            trace_id=ctx.trace_id,
            correlation_id=ctx.correlation_id,
            tx_id=ctx.tx_id,
            details=details or {},
        )
        with self._lock:
            self._audit_records.append(entry)
            self.logger.info(json.dumps(asdict(entry)))
        return entry

    def get_audit_trail(self) -> List[AuditLogEntry]:
        with self._lock:
            return list(self._audit_records)
