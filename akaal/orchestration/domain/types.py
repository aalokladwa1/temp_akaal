"""
Shared domain value objects and engine state enums for Enterprise Orchestration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, Any, Optional
import hashlib
import json


class EngineState(str, Enum):
    """
    Execution states only.
    State transitions are explicitly validated by the StateController.
    """
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"


class WorkflowStepName(str, Enum):
    """
    Business workflow phase identifiers executed by the Workflow Engine.
    Engine states and business workflow steps remain completely independent.
    """
    ANALYSIS = "ANALYSIS"
    PLANNING = "PLANNING"
    PRE_MIGRATION = "PRE_MIGRATION"
    MIGRATION = "MIGRATION"
    GB_VALIDATION = "GB_VALIDATION"
    CDC = "CDC"
    CUTOVER = "CUTOVER"
    POST_VALIDATION = "POST_VALIDATION"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class Version:
    number: int = 1

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("Version number must be greater than or equal to 1.")

    def increment(self) -> "Version":
        return Version(number=self.number + 1)

    def __int__(self) -> int:
        return self.number

    def __str__(self) -> str:
        return str(self.number)


@dataclass(frozen=True)
class Checksum:
    digest: str

    def __post_init__(self) -> None:
        if not self.digest or len(self.digest) != 64:
            raise ValueError("Checksum digest must be a 64-character SHA-256 hex string.")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checksum":
        """Compute deterministic SHA-256 checksum from a dictionary."""
        serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(serialized).hexdigest()
        return cls(digest=digest)

    @classmethod
    def from_bytes(cls, content: bytes) -> "Checksum":
        digest = hashlib.sha256(content).hexdigest()
        return cls(digest=digest)

    def __str__(self) -> str:
        return self.digest


@dataclass(frozen=True)
class AuditMetadata:
    created_by: str = "system"
    updated_by: str = "system"
    tenant_id: str = "default"
    correlation_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
