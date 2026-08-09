"""
AKAAL Gateway — Unified Event DTO Contracts & Progress Event Emitter
====================================================================
Establishes a single unified event architecture across Preflight, Schema Exec,
Transport, Validation, and Runtime state.
"""

from typing import Dict, Any, Optional
import time


class PreflightProgressDTO:
    """First-class Progress Event DTO for long-running Preflight & Discovery operations."""

    def __init__(
        self,
        operation_id: str,
        operation: str = "preflight",
        phase: str = "DISCOVERY",
        status: str = "RUNNING",
        schema: str = "",
        table: str = "",
        completed_objects: int = 0,
        total_objects: int = 0,
        message: str = "",
        timestamp: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.operation_id = operation_id
        self.operation = operation
        self.phase = phase
        self.status = status
        self.schema = schema
        self.table = table
        self.completed_objects = completed_objects
        self.total_objects = total_objects
        self.message = message
        self.timestamp = timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation": self.operation,
            "phase": self.phase,
            "status": self.status,
            "schema": self.schema,
            "table": self.table,
            "completed_objects": self.completed_objects,
            "total_objects": self.total_objects,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details
        }
