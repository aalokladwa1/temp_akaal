"""
NexusForge — Structured Message Model
=======================================
Every inter-agent communication must use this message format.
TRD Section 11: Every message shall include MessageID, CorrelationID,
ProjectID, MigrationID, Sender, Receiver, Timestamp, Priority, Checksum,
Payload Schema Version.

No agent may communicate outside this contract.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from akaal.core.models.enums import AgentType, Priority


# ---------------------------------------------------------------------------
# Message Schema Version — bump when payload structure changes
# ---------------------------------------------------------------------------
MESSAGE_SCHEMA_VERSION = "1.0.0"


def _utc_now() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _compute_checksum(data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 checksum of message payload.
    Excludes the 'checksum' field itself to avoid circular dependency.
    """
    payload_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Core Structured Message
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """
    The canonical inter-agent communication unit.

    Every agent MUST use this structure. Direct memory manipulation
    and unstructured calls are forbidden (manager_agent.md Section 9).
    """

    # Required routing fields
    sender: AgentType
    receiver: AgentType
    message_type: str                          # e.g. "TASK_ASSIGN", "TASK_RESULT"

    # Optional payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # IDs — auto-generated if not provided
    message_id: str = field(default_factory=_new_id)
    correlation_id: str = field(default_factory=_new_id)  # Links request↔response
    project_id: Optional[str] = None
    migration_id: Optional[str] = None

    # Metadata
    priority: Priority = Priority.P3_DISCOVERY
    timestamp: str = field(default_factory=_utc_now)
    schema_version: str = MESSAGE_SCHEMA_VERSION

    # Integrity — computed after construction
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        """Compute checksum after all fields are set."""
        self.checksum = self._compute()

    def _compute(self) -> str:
        """Build checksum from all fields except checksum itself."""
        data = {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "payload": self.payload,
        }
        return _compute_checksum(data)

    def verify_integrity(self) -> bool:
        """
        Verify message has not been tampered with.
        TRD Section 11: Every message shall be validated before processing.
        """
        expected = self._compute()
        return expected == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "sender": self.sender.value if isinstance(self.sender, AgentType) else self.sender,
            "receiver": self.receiver.value if isinstance(self.receiver, AgentType) else self.receiver,
            "message_type": self.message_type,
            "priority": self.priority.value if isinstance(self.priority, Priority) else self.priority,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "checksum": self.checksum,
        }

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize message from dictionary."""
        msg = cls(
            sender=AgentType(data["sender"]),
            receiver=AgentType(data["receiver"]),
            message_type=data["message_type"],
            payload=data.get("payload", {}),
            message_id=data["message_id"],
            correlation_id=data["correlation_id"],
            project_id=data.get("project_id"),
            migration_id=data.get("migration_id"),
            priority=Priority(data.get("priority", Priority.P3_DISCOVERY.value)),
            timestamp=data["timestamp"],
            schema_version=data.get("schema_version", MESSAGE_SCHEMA_VERSION),
        )
        # Restore original checksum for verification
        msg.checksum = data.get("checksum", "")
        return msg

    def __repr__(self) -> str:
        return (
            f"Message(type={self.message_type}, "
            f"from={self.sender.value}→{self.receiver.value}, "
            f"project={self.project_id}, "
            f"msg_id={self.message_id[:8]}...)"
        )


# ---------------------------------------------------------------------------
# Known Message Types — constants to avoid magic strings
# ---------------------------------------------------------------------------

class MessageType:
    # Manager → Agents
    TASK_ASSIGN           = "TASK_ASSIGN"
    TASK_CANCEL           = "TASK_CANCEL"
    WORKFLOW_PAUSE        = "WORKFLOW_PAUSE"
    WORKFLOW_RESUME       = "WORKFLOW_RESUME"
    CHECKPOINT_CREATE     = "CHECKPOINT_CREATE"
    CHECKPOINT_RESTORE    = "CHECKPOINT_RESTORE"
    APPROVAL_REQUEST      = "APPROVAL_REQUEST"
    HEALTH_CHECK_REQUEST  = "HEALTH_CHECK_REQUEST"

    # Agents → Manager
    TASK_RESULT           = "TASK_RESULT"
    TASK_FAILED           = "TASK_FAILED"
    HEALTH_CHECK_RESPONSE = "HEALTH_CHECK_RESPONSE"
    DISCOVERY_COMPLETE    = "DISCOVERY_COMPLETE"
    VALIDATION_COMPLETE   = "VALIDATION_COMPLETE"
    GB_IMPORT_COMPLETE    = "GB_IMPORT_COMPLETE"

    # System / Audit
    INCIDENT_CREATED      = "INCIDENT_CREATED"
    INCIDENT_RESOLVED     = "INCIDENT_RESOLVED"
    AUDIT_ENTRY           = "AUDIT_ENTRY"
    LOOP_WARNING          = "LOOP_WARNING"
    LOOP_ESCALATE         = "LOOP_ESCALATE"
    LOOP_FREEZE           = "LOOP_FREEZE"

    # Human
    APPROVAL_DECISION     = "APPROVAL_DECISION"
