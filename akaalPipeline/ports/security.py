"""akaalPipeline.ports.security
==============================
Security provider port protocol.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable
from akaalPipeline.security.context import PipelineActorContext


@runtime_checkable
class SecurityProviderPort(Protocol):
    def resolve_actor_context(self, raw_credential: str) -> Optional[PipelineActorContext]: ...
