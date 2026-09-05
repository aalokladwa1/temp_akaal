"""
akaalPipeline.api.rest.security
==================================
Builds an untrusted-wire ActorContext from an HTTP request. This context carries
CLAIMS only -- it becomes trusted only if PipelineUnifiedCaller._resolve_trusted_actor()
independently re-derives it through the durable SessionManager (session_id + session_token).
This module never marks anything AUTHENTICATED itself; that would violate
DESERIALIZATION != AUTHENTICATION.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Header

from akaalIPC.security.context import ActorContext, ActorReference


def build_actor_context(
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-Id"),
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    x_environment: Optional[str] = Header(default=None, alias="X-Environment"),
) -> ActorContext:
    session_token = None
    if authorization and authorization.lower().startswith("bearer "):
        session_token = authorization[7:].strip()

    # actor_id is a claim, not a grant -- if no session is presented, this resolves to an
    # anonymous/unauthenticated actor via PipelineActorContext.from_ipc's trusted_boundary=False
    # downgrade (or SESSION_AUTHENTICATION_REJECTED if a session_id/token pair fails verification).
    actor_ref = ActorReference(
        actor_id=x_session_id or "anonymous",
        actor_type="HUMAN",
    )
    return ActorContext(
        actor=actor_ref,
        organization_id=x_tenant_id,
        workspace_id=x_workspace_id,
        project_id=x_project_id,
        environment=x_environment,
        session_id=x_session_id,
        session_token=session_token,
        provenance="rest-api",
    )
