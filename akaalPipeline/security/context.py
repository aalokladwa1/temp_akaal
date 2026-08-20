"""akaalPipeline.security.context
==============================
Pipeline actor context model, adapting akaalIPC.security.ActorContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple
from akaalIPC.security.context import ActorContext as IPCActorContext


@dataclass(frozen=True)
class PipelineActorContext:
    actor_id: str
    actor_type: str
    display_name: Optional[str] = None
    organization_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    environment: Optional[str] = None
    roles: Tuple[str, ...] = field(default_factory=tuple)
    scopes: Tuple[str, ...] = field(default_factory=tuple)
    session_id: Optional[str] = None
    provenance: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("PipelineActorContext.actor_id cannot be empty")
        if not self.actor_type:
            raise ValueError("PipelineActorContext.actor_type cannot be empty")
        object.__setattr__(self, "roles", tuple(self.roles) if self.roles else ())
        object.__setattr__(self, "scopes", tuple(self.scopes) if self.scopes else ())

    @classmethod
    def from_ipc(cls, ipc_actor: IPCActorContext) -> PipelineActorContext:
        ref = ipc_actor.actor
        return cls(
            actor_id=ref.actor_id,
            actor_type=ref.actor_type,
            display_name=ref.display_name,
            organization_id=ipc_actor.organization_id,
            workspace_id=ipc_actor.workspace_id,
            project_id=ipc_actor.project_id,
            environment=ipc_actor.environment,
            roles=ipc_actor.roles,
            scopes=ipc_actor.scopes,
            session_id=ipc_actor.session_id,
            provenance=ipc_actor.provenance,
        )

    def to_dict(self) -> dict:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "display_name": self.display_name,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "environment": self.environment,
            "roles": list(self.roles),
            "scopes": list(self.scopes),
            "session_id": self.session_id,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PipelineActorContext:
        return cls(
            actor_id=data["actor_id"],
            actor_type=data["actor_type"],
            display_name=data.get("display_name"),
            organization_id=data.get("organization_id"),
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            environment=data.get("environment"),
            roles=tuple(data.get("roles", ())),
            scopes=tuple(data.get("scopes", ())),
            session_id=data.get("session_id"),
            provenance=data.get("provenance"),
        )
