"""akaalPipeline.contracts.correlation
====================================
Correlation identity for pipeline tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from akaalIPC.security.context import CorrelationContext as IPCCorrelationContext


@dataclass(frozen=True)
class PipelineCorrelationContext:
    request_id: str
    correlation_id: str
    causation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_ipc(cls, ipc_corr: IPCCorrelationContext) -> PipelineCorrelationContext:
        return cls(
            request_id=ipc_corr.request_id,
            correlation_id=ipc_corr.correlation_id,
            causation_id=ipc_corr.causation_id,
            trace_id=ipc_corr.trace_id,
            span_id=ipc_corr.span_id,
            timestamp=ipc_corr.timestamp,
        )

    @classmethod
    def new(cls, *, causation_id: Optional[str] = None) -> PipelineCorrelationContext:
        return cls(
            request_id=f"req-{uuid.uuid4().hex}",
            correlation_id=f"corr-{uuid.uuid4().hex}",
            causation_id=causation_id,
        )
