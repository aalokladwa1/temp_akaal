"""
akaalEngine.gateway.models.context
==================================
Canonical Gateway request execution context.
Preserves identity, fencing epochs, cancellation tokens, and request metadata across orchestration chains.
"""

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GatewayRequestContext:
    """Canonical execution context for any request entering EngineGateway."""
    migration_id: str
    run_id: str
    job_id: Optional[str] = None
    tenant_id: Optional[str] = None
    operation_id: str = field(default_factory=lambda: f"op-{uuid.uuid4().hex[:12]}")
    fencing_epoch: Optional[int] = None
    cancellation_event: Optional[threading.Event] = None
    execution_mode: Optional[str] = None
    request_timestamp: float = field(default_factory=time.time)
    deadline_seconds: Optional[float] = None

    def is_cancelled(self) -> bool:
        """Checks whether cancellation has been signaled for this context."""
        return self.cancellation_event is not None and self.cancellation_event.is_set()
