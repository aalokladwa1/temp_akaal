"""akaalPipeline.operations.models
================================
Operation journal record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from akaalPipeline.contracts.enums import OperationStatus
from akaalPipeline.security.context import PipelineActorContext


@dataclass
class OperationRecord:
    operation_id: str
    command_id: str
    idempotency_key: Optional[str]
    status: OperationStatus
    actor: PipelineActorContext
    payload_fingerprint: str
    result_payload: Optional[Mapping[str, Any]] = None
    error: Optional[Mapping[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "command_id": self.command_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "actor": self.actor.to_dict(),
            "payload_fingerprint": self.payload_fingerprint,
            "result_payload": dict(self.result_payload) if self.result_payload is not None else None,
            "error": dict(self.error) if self.error is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OperationRecord:
        return cls(
            operation_id=data["operation_id"],
            command_id=data["command_id"],
            idempotency_key=data.get("idempotency_key"),
            status=OperationStatus(data["status"]),
            actor=PipelineActorContext.from_dict(data["actor"]),
            payload_fingerprint=data["payload_fingerprint"],
            result_payload=data.get("result_payload"),
            error=data.get("error"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
